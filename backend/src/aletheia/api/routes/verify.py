"""Verification endpoint: ground a claim against evidence through the pipeline.

Phase 2 lets the endpoint source its own evidence. If the caller supplies ``evidence``
it is judged against exactly that text (the Phase 1 behaviour); if it is omitted, the
Retriever searches the curated corpus and the verdicts are grounded in what it finds.
Either way the thesis holds: every verdict is grounded in a quoted span or reported as
Unverifiable. The response additively carries the retrieved ``citations`` — the verdict
contract itself is unchanged. The pipeline is built once from settings and reused; a
missing provider key surfaces as a clear 503 rather than a crash.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aletheia.agents import EvidenceRetriever, VerificationPipeline, VerificationResult
from aletheia.config import get_settings
from aletheia.corpus.retrieval import RetrievalConfig, RetrievedEvidence, Retriever
from aletheia.db.session import get_sessionmaker
from aletheia.embeddings import EmbeddingConfigurationError, build_embedder
from aletheia.llm import LLMConfigurationError, LLMError, build_llm_client

router = APIRouter(tags=["verification"])


class VerifyRequest(BaseModel):
    """A question, optional evidence to judge against, and an optional candidate answer."""

    query: str = Field(min_length=1, description="The question being answered.")
    evidence: str | None = Field(
        default=None,
        min_length=1,
        description="Source text the verdicts must cite. If omitted, the corpus is searched.",
    )
    candidate_answer: str | None = Field(
        default=None,
        description="Answer to verify. If omitted, the Generator produces one.",
    )


class Citation(BaseModel):
    """A corpus source retrieved as evidence, with its provenance and trust tier."""

    index: int = Field(description="1-based position in the formatted evidence block.")
    title: str
    connector: str
    external_id: str
    url: str | None = None
    trust_tier: str = Field(description="The trust tier the evidence carries (ADR-0003).")
    score: float = Field(description="Fused retrieval relevance (higher is more relevant).")


class VerifyResponse(VerificationResult):
    """The grounded verdict contract, enriched with the citations it was grounded in.

    Subclasses :class:`VerificationResult` so the verdict contract is unchanged — every
    existing field is still present at the top level — and only adds ``citations``, which
    is empty when the caller supplied their own evidence.
    """

    citations: list[Citation] = Field(
        default_factory=list,
        description="Corpus sources retrieved as evidence, in citation order.",
    )


def _build_evidence_retriever() -> EvidenceRetriever:
    """A corpus search bound to the process sessionmaker and embedder.

    Opens a short-lived session per query so the closure is safe to share across
    concurrent requests; the embedder and config are process-wide.
    """
    sessionmaker = get_sessionmaker()
    embedder = build_embedder()
    config = RetrievalConfig.from_settings(get_settings())

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        async with sessionmaker() as session:
            return await Retriever(session, embedder=embedder, config=config).search(query)

    return retrieve


@lru_cache
def _build_pipeline() -> VerificationPipeline:
    return VerificationPipeline(build_llm_client(), retrieve=_build_evidence_retriever())


def get_pipeline() -> VerificationPipeline:
    """Provide the shared pipeline, mapping a missing key to a 503 (overridable in tests)."""
    try:
        return _build_pipeline()
    except (LLMConfigurationError, EmbeddingConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _citations(sources: Sequence[RetrievedEvidence]) -> list[Citation]:
    return [
        Citation(
            index=index,
            title=source.title,
            connector=source.connector,
            external_id=source.external_id,
            url=source.url,
            trust_tier=source.trust_tier.value,
            score=source.score,
        )
        for index, source in enumerate(sources, start=1)
    ]


@router.post("/verify", response_model=VerifyResponse, summary="Verify claims against evidence")
async def verify(
    request: VerifyRequest,
    pipeline: Annotated[VerificationPipeline, Depends(get_pipeline)],
) -> VerifyResponse:
    """Decompose the answer into claims and ground each verdict in the evidence."""
    try:
        state = await pipeline.ainvoke(
            query=request.query,
            evidence=request.evidence,
            candidate_answer=request.candidate_answer,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result = state["result"]
    return VerifyResponse(
        query=result.query,
        candidate_answer=result.candidate_answer,
        verdicts=result.verdicts,
        citations=_citations(state.get("evidence_sources", [])),
    )
