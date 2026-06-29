"""Verification endpoint: ground a claim against evidence through the pipeline.

Phase 2 lets the endpoint source its own evidence. If the caller supplies ``evidence``
it is judged against exactly that text (the Phase 1 behaviour); if it is omitted, the
Retriever searches the curated corpus and the verdicts are grounded in what it finds.
Either way the thesis holds: every verdict is grounded in a quoted span or reported as
Unverifiable. The response additively carries the retrieved ``citations`` and a
guardrail ``safety`` advisory (with the standing medical-advice disclaimer) — the
verdict contract itself is unchanged. The pipeline is built once from settings and
reused; a missing provider key surfaces as a clear 503 rather than a crash.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aletheia.agents import (
    EvidenceRetriever,
    SafetyAssessment,
    VerificationPipeline,
    VerificationResult,
)
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
    """The grounded verdict contract, enriched with citations and a safety advisory.

    Subclasses :class:`VerificationResult` so the verdict contract is unchanged — every
    existing field is still present at the top level — and only adds ``citations`` (the
    sources the verdicts were grounded in, empty when the caller supplied their own
    evidence) and ``safety`` (the guardrail's advisory plus the standing disclaimer).
    """

    citations: list[Citation] = Field(
        default_factory=list,
        description="Corpus sources retrieved as evidence, in citation order.",
    )
    safety: SafetyAssessment = Field(
        description="Guardrail advisory and the standing medical-advice disclaimer."
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
        safety=state["safety"],
    )


def _serialize_stage(update: Mapping[str, Any]) -> dict[str, Any]:
    """Project a node's partial state into a JSON-safe payload for the stream.

    Each node contributes only the keys it produced, so this picks whichever are present —
    citations from the retriever, the answer/claims from the generator, verdicts from the
    verifier, the assembled result, and the guardrail's safety advisory.
    """
    payload: dict[str, Any] = {}
    if "evidence_sources" in update:
        citations = _citations(update["evidence_sources"])
        payload["citations"] = [citation.model_dump() for citation in citations]
    if "candidate_answer" in update:
        payload["candidate_answer"] = update["candidate_answer"]
    if "claims" in update:
        payload["claims"] = list(update["claims"])
    if "verdicts" in update:
        payload["verdicts"] = [verdict.model_dump() for verdict in update["verdicts"]]
    if "result" in update:
        payload["result"] = update["result"].model_dump()
    if "safety" in update:
        payload["safety"] = update["safety"].model_dump()
    return payload


def _sse(event: str, data: Mapping[str, Any]) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/verify/stream", summary="Stream the live verification path (SSE)")
async def verify_stream(
    request: VerifyRequest,
    pipeline: Annotated[VerificationPipeline, Depends(get_pipeline)],
) -> StreamingResponse:
    """Run the pipeline and stream each agent's output as a Server-Sent Event.

    Emits one event per graph node (``retriever``, ``generator``, ``verifier``,
    ``aggregator``, ``guardrail``) carrying that stage's partial result, then a final
    ``done`` event — or an ``error`` event if the model call fails. The non-streaming
    ``/verify`` contract is unchanged.
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for stage in pipeline.astream(
                request.query, request.evidence, request.candidate_answer
            ):
                yield _sse(stage.stage, _serialize_stage(stage.update))
        except LLMError as exc:
            yield _sse("error", {"detail": str(exc)})
            return
        yield _sse("done", {})

    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
