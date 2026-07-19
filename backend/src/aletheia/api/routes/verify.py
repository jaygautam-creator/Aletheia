"""Verification endpoint: ground a claim against evidence through the pipeline.

Phase 2 lets the endpoint source its own evidence. If the caller supplies ``evidence``
it is judged against exactly that text (the Phase 1 behaviour); if it is omitted, the
Retriever searches the curated medical corpus for an in-scope query, or (ADR-0012) a
live Wikipedia lookup for a general one — the Intake guard's scope classifier decides
which, and neither case is refused. Either way the thesis holds: every verdict is
grounded in a quoted span or reported as Unverifiable. The response additively carries
the retrieved ``citations``, a
``source_index`` on each verdict resolving its quoted span to the citation whose
evidence block contains it, and a guardrail ``safety`` advisory (with the standing
medical-advice disclaimer) — the verdict contract itself is unchanged. The pipeline is
built once from settings and reused; a missing provider key surfaces as a clear 503
rather than a crash.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.dependencies import get_current_user_optional
from aletheia.accounts.models import KeySource, Provider, User
from aletheia.accounts.repository import get_api_key, log_request
from aletheia.accounts.security import decrypt_key
from aletheia.agents import (
    EvidenceRetriever,
    SafetyAssessment,
    VerificationPipeline,
    VerificationResult,
)
from aletheia.agents.contracts import ClaimVerdict, normalise_whitespace
from aletheia.config import Settings, get_settings
from aletheia.corpus.live_wikipedia import live_wikipedia_search
from aletheia.corpus.retrieval import (
    RetrievalConfig,
    RetrievedEvidence,
    Retriever,
    format_evidence_block,
)
from aletheia.db.session import get_session, get_sessionmaker
from aletheia.embeddings import EmbeddingConfigurationError, build_embedder
from aletheia.llm import LLMConfigurationError, LLMError, build_llm_client
from aletheia.observability import timed_stages

logger = logging.getLogger(__name__)

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


class GroundedVerdict(ClaimVerdict):
    """A :class:`ClaimVerdict` enriched with the citation its quoted span resolves to.

    Additive and optional — the verdict contract itself is untouched.
    ``source_index`` is the 1-based position (matching :attr:`Citation.index`) of the
    retrieved evidence block that contains the quoted span, or ``None`` when the caller
    supplied raw evidence, the verdict quotes nothing, or the span cannot be located in
    a single block.
    """

    source_index: int | None = Field(
        default=None,
        description="1-based citation index whose evidence block contains the quoted span.",
    )


class VerifyResponse(VerificationResult):
    """The grounded verdict contract, enriched with citations and a safety advisory.

    Subclasses :class:`VerificationResult` so the verdict contract is unchanged — every
    existing field is still present at the top level — and only adds ``citations`` (the
    sources the verdicts were grounded in, empty when the caller supplied their own
    evidence), a ``source_index`` on each verdict linking its span to a citation, and
    ``safety`` (the guardrail's advisory plus the standing disclaimer).
    """

    # A narrowing, additive override: every GroundedVerdict is a valid ClaimVerdict.
    verdicts: list[GroundedVerdict] = Field(  # type: ignore[assignment]
        description="Per-claim verdicts, each linking its quoted span to a citation."
    )
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
    return VerificationPipeline(
        build_llm_client(),
        retrieve=_build_evidence_retriever(),
        general_retrieve=live_wikipedia_search,
        enable_scope_guard=get_settings().scope_guard_enabled,
    )


def get_pipeline() -> VerificationPipeline:
    """Provide the shared pipeline, mapping a missing key to a 503 (overridable in tests)."""
    try:
        return _build_pipeline()
    except (LLMConfigurationError, EmbeddingConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@dataclass
class PipelineChoice:
    """The pipeline to run a request through, plus what it will be logged as."""

    pipeline: VerificationPipeline
    key_source: KeySource
    provider: str


async def get_pipeline_for_request(
    default_pipeline: Annotated[VerificationPipeline, Depends(get_pipeline)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PipelineChoice:
    """Prefer the signed-in user's own provider key over the server default, if stored.

    A BYO key means a fresh, uncached pipeline (the client construction is cheap; only
    the LLM key differs), built for this request only and then discarded — the shared,
    cached pipeline keeps serving every anonymous or key-less request unchanged.
    """
    if user is not None:
        stored = await get_api_key(session, user.id, Provider(settings.llm_provider))
        if stored is not None:
            api_key = decrypt_key(stored.encrypted_key, settings=settings)
            pipeline = VerificationPipeline(
                build_llm_client(settings, override_key=api_key),
                retrieve=_build_evidence_retriever(),
                enable_scope_guard=settings.scope_guard_enabled,
            )
            return PipelineChoice(
                pipeline=pipeline, key_source=KeySource.USER_KEY, provider=settings.llm_provider
            )
    return PipelineChoice(
        pipeline=default_pipeline,
        key_source=KeySource.SERVER_DEFAULT,
        provider=settings.llm_provider,
    )


async def _log(  # noqa: PLR0913
    session: AsyncSession,
    *,
    user: User | None,
    route: str,
    query: str,
    key_source: KeySource,
    provider: str,
    status: str,
    started_at: float,
) -> None:
    try:
        await log_request(
            session,
            user_id=user.id if user else None,
            route=route,
            query_preview=query,
            key_source=key_source,
            provider=provider,
            status=status,
            latency_ms=int((time.monotonic() - started_at) * 1000),
        )
    except Exception:
        logger.exception("failed to write request history; the response is unaffected")


def _source_index_for(span: str | None, sources: Sequence[RetrievedEvidence]) -> int | None:
    """Resolve a quoted span to the first numbered evidence block that contains it.

    Matching mirrors the grounding check exactly: each candidate is the same block the
    Verifier saw (:func:`format_evidence_block`, header line included, so a span that
    straddles the title line still resolves) under the same whitespace normalisation.
    A span present in more than one block resolves to the first; a span found in no
    single block (e.g. one straddling two blocks) resolves to ``None`` — the link is
    omitted rather than guessed.
    """
    if not span or not sources:
        return None
    needle = normalise_whitespace(span)
    for index, source in enumerate(sources, start=1):
        if needle in normalise_whitespace(format_evidence_block(index, source)):
            return index
    return None


def _with_source_indices(
    verdicts: Sequence[ClaimVerdict], sources: Sequence[RetrievedEvidence]
) -> list[GroundedVerdict]:
    """Enrich verdicts with the citation index each quoted span resolves to."""
    return [
        GroundedVerdict(
            **verdict.model_dump(),
            source_index=_source_index_for(verdict.quoted_span, sources),
        )
        for verdict in verdicts
    ]


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
    choice: Annotated[PipelineChoice, Depends(get_pipeline_for_request)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VerifyResponse:
    """Decompose the answer into claims and ground each verdict in the evidence."""
    started_at = time.monotonic()
    try:
        state = await choice.pipeline.ainvoke(
            query=request.query,
            evidence=request.evidence,
            candidate_answer=request.candidate_answer,
        )
    except LLMError as exc:
        await _log(
            session,
            user=user,
            route="/verify",
            query=request.query,
            key_source=choice.key_source,
            provider=choice.provider,
            status="error",
            started_at=started_at,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result = state["result"]
    sources = state.get("evidence_sources", [])
    await _log(
        session,
        user=user,
        route="/verify",
        query=request.query,
        key_source=choice.key_source,
        provider=choice.provider,
        status="refused" if result.refused else "ok",
        started_at=started_at,
    )
    return VerifyResponse(
        query=result.query,
        candidate_answer=result.candidate_answer,
        verdicts=_with_source_indices(result.verdicts, sources),
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        citations=_citations(sources),
        safety=state["safety"],
    )


def _serialize_stage(
    update: Mapping[str, Any], sources: Sequence[RetrievedEvidence]
) -> dict[str, Any]:
    """Project a node's partial state into a JSON-safe payload for the stream.

    Each node contributes only the keys it produced, so this picks whichever are present —
    citations from the retriever, the answer/claims from the generator, verdicts from the
    verifier, the assembled result, and the guardrail's safety advisory. ``sources`` is
    the evidence retrieved earlier in the *same* stream (empty when the caller supplied
    raw evidence); each verdict payload additively carries the ``source_index`` its
    quoted span resolves to.
    """
    payload: dict[str, Any] = {}
    if "intake" in update:
        payload["intake"] = update["intake"].model_dump()
    if "evidence_sources" in update:
        citations = _citations(update["evidence_sources"])
        payload["citations"] = [citation.model_dump() for citation in citations]
    if "candidate_answer" in update:
        payload["candidate_answer"] = update["candidate_answer"]
    if "claims" in update:
        payload["claims"] = list(update["claims"])
    if "verdicts" in update:
        payload["verdicts"] = [
            verdict.model_dump() for verdict in _with_source_indices(update["verdicts"], sources)
        ]
    if "result" in update:
        result_payload = update["result"].model_dump()
        result_payload["verdicts"] = [
            verdict.model_dump()
            for verdict in _with_source_indices(update["result"].verdicts, sources)
        ]
        payload["result"] = result_payload
    if "safety" in update:
        payload["safety"] = update["safety"].model_dump()
    return payload


def _sse(event: str, data: Mapping[str, Any]) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/verify/stream", summary="Stream the live verification path (SSE)")
async def verify_stream(
    request: VerifyRequest,
    choice: Annotated[PipelineChoice, Depends(get_pipeline_for_request)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StreamingResponse:
    """Run the pipeline and stream each agent's output as a Server-Sent Event.

    Emits one event per graph node (``retriever``, ``generator``, ``verifier``,
    ``aggregator``, ``guardrail``) carrying that stage's partial result, then a final
    ``done`` event — or an ``error`` event if the model call fails. The non-streaming
    ``/verify`` contract is unchanged.
    """

    async def event_stream() -> AsyncIterator[str]:
        # Retrieved evidence arrives on the retriever's event; hold onto it so the
        # later verifier/aggregator events can link each span to its source block.
        sources: Sequence[RetrievedEvidence] = []
        started_at = time.monotonic()
        status = "ok"
        try:
            # timed_stages records each node's duration into the Prometheus histogram —
            # the same timings the browser derives from event arrival, kept server-side.
            async for stage in timed_stages(
                choice.pipeline.astream(request.query, request.evidence, request.candidate_answer)
            ):
                if "evidence_sources" in stage.update:
                    sources = stage.update["evidence_sources"]
                if "result" in stage.update and stage.update["result"].refused:
                    status = "refused"
                yield _sse(stage.stage, _serialize_stage(stage.update, sources))
        except LLMError as exc:
            yield _sse("error", {"detail": str(exc)})
            await _log(
                session,
                user=user,
                route="/verify/stream",
                query=request.query,
                key_source=choice.key_source,
                provider=choice.provider,
                status="error",
                started_at=started_at,
            )
            return
        except Exception as exc:
            # The HTTP status is already 200 and the body is mid-flight, so any later
            # failure (e.g. the Retriever's corpus database is unreachable) must be
            # reported as a terminal error event rather than silently dropping the
            # connection — which the browser would only see as a generic network error.
            logger.exception("verification stream failed")
            yield _sse("error", {"detail": f"Verification failed ({type(exc).__name__})."})
            await _log(
                session,
                user=user,
                route="/verify/stream",
                query=request.query,
                key_source=choice.key_source,
                provider=choice.provider,
                status="error",
                started_at=started_at,
            )
            return
        yield _sse("done", {})
        await _log(
            session,
            user=user,
            route="/verify/stream",
            query=request.query,
            key_source=choice.key_source,
            provider=choice.provider,
            status=status,
            started_at=started_at,
        )

    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
