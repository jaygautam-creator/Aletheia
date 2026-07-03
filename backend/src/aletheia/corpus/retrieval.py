"""Hybrid retrieval: semantic + keyword search fused with Reciprocal Rank Fusion.

Two ranked candidate lists are produced from the same ``chunk`` table — one ordered by
vector cosine similarity (pgvector, the HNSW index), one by full-text keyword relevance
(the generated ``tsvector``, the GIN index) — then merged with Reciprocal Rank Fusion
(RRF). RRF needs only ranks, not comparable scores, so the two very different scoring
scales (cosine distance vs. ``ts_rank``) never have to be reconciled, and a chunk that
both branches like is rewarded over one that only a single branch ranks highly.

The pieces are split the same way the ingestion pipeline is, so the logic is testable
without a database:

* :func:`reciprocal_rank_fusion` (the fusion math) and :func:`to_evidence` (assembling
  results from hydrated chunks) are pure and unit-tested offline.
* :class:`Retriever` holds the two SQL branches and is exercised by the Postgres
  integration tests.

Every result is a :class:`RetrievedEvidence` carrying its source's trust tier: there is
no untiered evidence (ADR-0003).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from aletheia.config import Settings
from aletheia.corpus.models import Chunk, Document, TrustTier
from aletheia.embeddings.base import Embedder

#: Reciprocal Rank Fusion constant from the original RRF paper (Cormack et al., 2009): a
#: robust default, large enough that no single top rank dominates the fusion yet small
#: enough that rank order still matters.
DEFAULT_RRF_K = 60
#: How many fused results are returned as evidence by default.
DEFAULT_TOP_K = 8
#: Candidate pool pulled from each branch before fusion, by default.
DEFAULT_CANDIDATES = 20


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    """Tunables for one hybrid search.

    ``candidates`` is the per-branch pool size pulled before fusion; ``top_k`` is how
    many fused results are returned; ``rrf_k`` is the Reciprocal Rank Fusion constant.
    """

    top_k: int = DEFAULT_TOP_K
    candidates: int = DEFAULT_CANDIDATES
    rrf_k: int = DEFAULT_RRF_K

    @classmethod
    def from_settings(cls, settings: Settings) -> RetrievalConfig:
        """Build the config from application settings."""
        return cls(
            top_k=settings.retrieval_top_k,
            candidates=settings.retrieval_candidates,
            rrf_k=settings.rrf_k,
        )


#: Module-level default so it can serve as an argument default without re-allocating.
DEFAULT_RETRIEVAL = RetrievalConfig()


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    """One chunk returned by hybrid retrieval, with its provenance and trust tier.

    This is the unit the Retriever returns and the Verifier ultimately quotes. The
    ``trust_tier`` travels with every result so downstream code never handles untiered
    evidence (ADR-0003); ``score`` is the fused RRF score (higher is more relevant).
    """

    chunk_id: int
    source_id: int
    connector: str
    external_id: str
    title: str
    url: str | None
    trust_tier: TrustTier
    kind: str
    text: str
    score: float


def reciprocal_rank_fusion[Key](
    rankings: Sequence[Sequence[Key]], *, k: int = DEFAULT_RRF_K
) -> list[tuple[Key, float]]:
    """Fuse several ranked lists into one by Reciprocal Rank Fusion.

    Each item contributes ``1 / (k + rank)`` (rank 1-based) from every list it appears
    in, and the contributions are summed across lists; an item missing from a list adds
    nothing for it. Returns ``(item, score)`` pairs sorted by score descending, with ties
    broken by first appearance so the fusion is deterministic.
    """
    if k <= 0:
        raise ValueError("rrf_k must be positive.")

    scores: dict[Key, float] = {}
    first_seen: dict[Key, int] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(item, len(first_seen))
    return sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))


def to_evidence(
    ranked: Sequence[tuple[int, float]], chunks_by_id: Mapping[int, Chunk]
) -> list[RetrievedEvidence]:
    """Assemble :class:`RetrievedEvidence` from a fused ranking and hydrated chunks.

    Pure and order-preserving: walks ``ranked`` (already sorted by fused score) and reads
    each chunk's provenance from its loaded ``document -> source`` graph. A chunk id with
    no entry in ``chunks_by_id`` is skipped, so a stale id never raises.
    """
    evidence: list[RetrievedEvidence] = []
    for chunk_id, score in ranked:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            continue
        source = chunk.document.source
        evidence.append(
            RetrievedEvidence(
                chunk_id=chunk.id,
                source_id=source.id,
                connector=source.connector,
                external_id=source.external_id,
                title=source.title,
                url=source.url,
                trust_tier=source.trust_tier,
                kind=chunk.document.kind,
                text=chunk.text,
                score=score,
            )
        )
    return evidence


def format_evidence_block(index: int, source: RetrievedEvidence) -> str:
    """One numbered evidence block — the exact unit the Verifier quotes from.

    Shared by :func:`format_evidence` and the API layer's span→source resolution, so
    the block a span is searched in can never drift from the block the Verifier saw.
    """
    return f"[{index}] {source.title}\n{source.text}"


def format_evidence(sources: Sequence[RetrievedEvidence]) -> str:
    """Render retrieved evidence as the single text block the Verifier grounds against.

    Each source becomes a numbered block — a short provenance header followed by the
    chunk text *verbatim* — so a span the Verifier quotes from the text is still found
    by the grounding check, which only normalises whitespace. Returns ``""`` when there
    are no sources, which correctly leaves the Verifier with nothing to cite and so
    forces every verdict to ``Unverifiable``.
    """
    blocks = [format_evidence_block(index, source) for index, source in enumerate(sources, start=1)]
    return "\n\n".join(blocks)


class Retriever:
    """Hybrid (semantic + keyword) retrieval over the chunk corpus.

    Construct with an open :class:`AsyncSession` and the *same* embedder the corpus was
    built with — query and document vectors must share an embedding space. ``search``
    embeds the query, pulls a candidate pool from each branch, fuses them with RRF, and
    returns the top ``config.top_k`` results as trust-tiered :class:`RetrievedEvidence`.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        embedder: Embedder,
        config: RetrievalConfig = DEFAULT_RETRIEVAL,
    ) -> None:
        self._session = session
        self._embedder = embedder
        self._config = config

    async def search(self, query: str) -> list[RetrievedEvidence]:
        """Return the top trust-tiered evidence for ``query``, best first."""
        cleaned = query.strip()
        if not cleaned:
            return []

        query_vector = await self._embedder.embed_query(cleaned)
        semantic = await self._semantic_candidates(query_vector)
        keyword = await self._keyword_candidates(cleaned)

        fused = reciprocal_rank_fusion([semantic, keyword], k=self._config.rrf_k)
        top = fused[: self._config.top_k]
        if not top:
            return []

        chunks = await self._hydrate(chunk_id for chunk_id, _ in top)
        return to_evidence(top, chunks)

    async def _semantic_candidates(self, query_vector: Sequence[float]) -> list[int]:
        """Chunk ids ranked nearest-first by vector cosine distance (pgvector / HNSW)."""
        rows = await self._session.scalars(
            select(Chunk.id)
            .where(Chunk.embedding.isnot(None))
            .order_by(Chunk.embedding.cosine_distance(query_vector))
            .limit(self._config.candidates)
        )
        return list(rows)

    async def _keyword_candidates(self, query: str) -> list[int]:
        """Chunk ids ranked by full-text keyword relevance (tsvector / GIN)."""
        ts_query = func.plainto_tsquery("english", query)
        rows = await self._session.scalars(
            select(Chunk.id)
            .where(Chunk.content_tsv.op("@@")(ts_query))
            .order_by(func.ts_rank(Chunk.content_tsv, ts_query).desc())
            .limit(self._config.candidates)
        )
        return list(rows)

    async def _hydrate(self, chunk_ids: Iterable[int]) -> dict[int, Chunk]:
        """Load the chunks (with their ``document -> source`` graph) for ``chunk_ids``."""
        ids = list(chunk_ids)
        if not ids:
            return {}
        rows = await self._session.scalars(
            select(Chunk)
            .where(Chunk.id.in_(ids))
            .options(selectinload(Chunk.document).selectinload(Document.source))
        )
        return {chunk.id: chunk for chunk in rows}
