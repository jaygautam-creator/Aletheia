"""Verification endpoint: run a claim and its evidence through the grounded pipeline.

In Phase 1 the evidence is supplied by the caller (there is no retriever yet), so this
endpoint exposes exactly the thesis: every verdict it returns is grounded in a quoted
span of that evidence, or it is reported as Unverifiable. The pipeline is built once
from settings and reused; a missing provider key surfaces as a clear 503 rather than a
crash.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aletheia.agents import VerificationPipeline, VerificationResult
from aletheia.llm import LLMConfigurationError, LLMError, build_llm_client

router = APIRouter(tags=["verification"])


class VerifyRequest(BaseModel):
    """A question, the evidence to judge against, and an optional candidate answer."""

    query: str = Field(min_length=1, description="The question being answered.")
    evidence: str = Field(min_length=1, description="Source text the verdicts must cite.")
    candidate_answer: str | None = Field(
        default=None,
        description="Answer to verify. If omitted, the Generator produces one.",
    )


@lru_cache
def _build_pipeline() -> VerificationPipeline:
    return VerificationPipeline(build_llm_client())


def get_pipeline() -> VerificationPipeline:
    """Provide the shared pipeline, mapping a missing key to a 503 (overridable in tests)."""
    try:
        return _build_pipeline()
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/verify", response_model=VerificationResult, summary="Verify claims against evidence")
async def verify(
    request: VerifyRequest,
    pipeline: Annotated[VerificationPipeline, Depends(get_pipeline)],
) -> VerificationResult:
    """Decompose the answer into claims and ground each verdict in the evidence."""
    try:
        return await pipeline.run(
            query=request.query,
            evidence=request.evidence,
            candidate_answer=request.candidate_answer,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
