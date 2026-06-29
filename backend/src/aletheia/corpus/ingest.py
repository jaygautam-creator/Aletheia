"""The ingestion pipeline: fetched sources → chunks → embeddings → stored corpus.

Two layers, kept apart so the logic can be unit-tested without a database:

* :func:`assemble_source` is pure — it chunks a :class:`FetchedSource`, embeds the
  chunks, and builds the in-memory ``Source -> Document -> Chunk`` ORM graph, tagging it
  ``CURATED_CORPUS`` (ADR-0003). No session, no Postgres.
* :func:`ingest` persists assembled sources idempotently: a source already present
  (same connector + external id) is skipped unless ``replace=True``, so re-running the
  ingest never duplicates the corpus.

Both report what they did via :class:`IngestReport`, which the manifest is built from.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.corpus.chunking import DEFAULT_CHUNKING, ChunkConfig, chunk_text
from aletheia.corpus.connectors.base import FetchedSource
from aletheia.corpus.models import Chunk, Document, Source, TrustTier
from aletheia.embeddings.base import Embedder

SourceStatus = Literal["created", "replaced", "skipped"]


@dataclass(frozen=True, slots=True)
class SourceReport:
    """What happened to one source during an ingest run."""

    connector: str
    external_id: str
    title: str
    documents: int
    chunks: int
    status: SourceStatus


@dataclass(frozen=True, slots=True)
class IngestReport:
    """A summary of an ingest run, and the basis for the corpus manifest."""

    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    sources: list[SourceReport] = field(default_factory=list)

    @property
    def total_documents(self) -> int:
        return sum(source.documents for source in self.sources)

    @property
    def total_chunks(self) -> int:
        return sum(source.chunks for source in self.sources)


async def assemble_source(
    fetched: FetchedSource,
    *,
    embedder: Embedder,
    chunking: ChunkConfig = DEFAULT_CHUNKING,
    trust_tier: TrustTier = TrustTier.CURATED_CORPUS,
) -> Source:
    """Chunk, embed, and build the ORM graph for one source (no persistence).

    All chunks across the source's documents are embedded in a single batch to amortize
    model/API overhead, then distributed back to their documents in order.
    """
    chunked = [
        (doc, chunk_text(doc.text, max_chars=chunking.max_chars, overlap=chunking.overlap))
        for doc in fetched.documents
    ]
    flat = [text for _, texts in chunked for text in texts]
    vectors = await embedder.embed_documents(flat) if flat else []

    source = Source(
        connector=fetched.connector,
        external_id=fetched.external_id,
        title=fetched.title,
        url=fetched.url,
        license=fetched.license,
        trust_tier=trust_tier,
        meta=dict(fetched.meta),
    )

    cursor = 0
    for doc_ordinal, (raw, texts) in enumerate(chunked):
        document = Document(kind=raw.kind, ordinal=doc_ordinal, text=raw.text)
        for chunk_ordinal, text in enumerate(texts):
            document.chunks.append(
                Chunk(ordinal=chunk_ordinal, text=text, embedding=vectors[cursor])
            )
            cursor += 1
        source.documents.append(document)
    return source


async def ingest(
    session: AsyncSession,
    sources: Sequence[FetchedSource],
    *,
    embedder: Embedder,
    chunking: ChunkConfig = DEFAULT_CHUNKING,
    replace: bool = False,
) -> IngestReport:
    """Persist ``sources`` idempotently and return a report of the run.

    Everything a connector produces is stored as curated-corpus evidence (ADR-0003).
    Existing sources are skipped unless ``replace`` is set, in which case the old source
    (and its documents/chunks, via cascade) is deleted and rebuilt. The whole run commits
    once at the end.
    """
    report = IngestReport(
        embedding_provider=embedder.provider,
        embedding_model=embedder.model,
        embedding_dimension=embedder.dimension,
    )

    for fetched in sources:
        existing = await session.scalar(
            select(Source).where(
                Source.connector == fetched.connector,
                Source.external_id == fetched.external_id,
            )
        )
        if existing is not None and not replace:
            report.sources.append(await _existing_report(session, existing, "skipped"))
            continue
        if existing is not None:
            await session.delete(existing)
            await session.flush()

        source = await assemble_source(fetched, embedder=embedder, chunking=chunking)
        session.add(source)
        await session.flush()
        report.sources.append(
            SourceReport(
                connector=source.connector,
                external_id=source.external_id,
                title=source.title,
                documents=len(source.documents),
                chunks=sum(len(document.chunks) for document in source.documents),
                status="replaced" if existing is not None else "created",
            )
        )

    await session.commit()
    return report


async def _existing_report(
    session: AsyncSession, source: Source, status: SourceStatus
) -> SourceReport:
    """Report a source that is already in the corpus, counting its rows via the DB."""
    documents = await session.scalar(
        select(func.count(Document.id)).where(Document.source_id == source.id)
    )
    chunks = await session.scalar(
        select(func.count(Chunk.id))
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.source_id == source.id)
    )
    return SourceReport(
        connector=source.connector,
        external_id=source.external_id,
        title=source.title,
        documents=documents or 0,
        chunks=chunks or 0,
        status=status,
    )
