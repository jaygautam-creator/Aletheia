"""The Verifier node — where evidence grounding is enforced.

For each claim the Verifier asks the model for a verdict and a verbatim quoted span,
then applies two layers of defence so the system can never emit an ungrounded verdict:

1. If the model asserts ``Supported``/``Contradicted`` without supplying a span, the
   verdict is treated as ``Unverifiable`` — a claim of support with no quote is not
   support.
2. The verdict is run through :meth:`ClaimVerdict.grounded_against`, which downgrades
   it to ``Unverifiable`` if the quoted span is not present verbatim in the evidence.
   A fabricated quote cannot launder a claim into being supported.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from aletheia.agents.contracts import GROUNDED_VERDICTS, ClaimVerdict, Verdict
from aletheia.agents.prompts import verify_messages
from aletheia.agents.state import PipelineState
from aletheia.llm import LLMClient, LLMError

VerifierNode = Callable[[PipelineState], Awaitable[PipelineState]]


def _parse_verdict(value: object) -> Verdict:
    if isinstance(value, str):
        normalised = value.strip().capitalize()
        for verdict in Verdict:
            if verdict.value == normalised:
                return verdict
    raise LLMError(f"Verifier returned an unrecognised verdict: {value!r}")


def _as_span(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _as_reasoning(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "No reasoning provided."


def _coerce_verdict(claim: str, data: object, evidence: str) -> ClaimVerdict:
    """Turn a model's raw JSON judgement into a grounded, contract-valid verdict."""
    if not isinstance(data, dict):
        raise LLMError(f"Verifier expected a JSON object, got {type(data).__name__}.")

    verdict = _parse_verdict(data.get("verdict"))
    span = _as_span(data.get("quoted_span"))
    reasoning = _as_reasoning(data.get("reasoning"))

    # Defence 1: a grounded verdict with no span is not grounded.
    if verdict in GROUNDED_VERDICTS and span is None:
        return ClaimVerdict(
            claim=claim,
            verdict=Verdict.UNVERIFIABLE,
            quoted_span=None,
            reasoning=(
                f"Verifier claimed {verdict.value} but quoted no span; "
                f"treated as Unverifiable. {reasoning}"
            ),
        )

    if verdict is Verdict.UNVERIFIABLE:
        span = None

    # Defence 2: downgrade if the quoted span is not verbatim in the evidence.
    return ClaimVerdict(
        claim=claim, verdict=verdict, quoted_span=span, reasoning=reasoning
    ).grounded_against(evidence)


def make_verifier_node(llm: LLMClient) -> VerifierNode:
    """Build the Verifier node bound to a specific LLM client."""

    async def verifier(state: PipelineState) -> PipelineState:
        evidence = state["evidence"]
        claims = state["claims"]
        # Each claim is an independent, network-bound LLM call, so verify them
        # concurrently instead of sequentially: wall time becomes ~one call rather than
        # the sum of N. gather preserves input order, so verdicts still line up with
        # claims; a failure in any call propagates (then the fallback client, if any,
        # absorbs a transient error) exactly as the sequential loop did.
        judgements = await asyncio.gather(
            *(llm.generate_json(verify_messages(claim, evidence)) for claim in claims)
        )
        verdicts = [
            _coerce_verdict(claim, judgement, evidence)
            for claim, judgement in zip(claims, judgements, strict=True)
        ]
        return {"verdicts": verdicts}

    return verifier
