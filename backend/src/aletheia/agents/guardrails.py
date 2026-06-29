"""Output guardrails — the final safety layer over a verification result.

Grounding is enforced upstream in the Verifier (a verdict cannot affirm a claim without
quoting evidence). This layer sits at the *end* of the graph and does the complementary
job: it reads the assembled result and tells the caller how cautiously to treat it, and
it attaches the standing medical-advice disclaimer. It is deliberately **non-mutating** —
it never edits a verdict or the answer, so the verdict contract is untouched; it only adds
an advisory. Aletheia grounds claims in the literature, it does not practise medicine, and
this is where that boundary is made explicit on every response.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from aletheia.agents.contracts import Verdict, VerificationResult

if TYPE_CHECKING:
    from aletheia.agents.state import PipelineState

#: The standing disclaimer attached to every verification and surfaced in service
#: metadata. Aletheia is a research/grounding tool, not a clinician.
DISCLAIMER = (
    "Aletheia grounds claims in a curated medical-literature corpus; it is not a "
    "clinician and does not provide medical advice. Verdicts reflect only what the cited "
    "evidence supports and may be incomplete or out of date. Consult a qualified health "
    "professional before making any medical decision."
)


class Advisory(StrEnum):
    """How cautiously the caller should treat a verification result.

    Escalates with risk: ``INFO`` when every claim is grounded as Supported, ``CAUTION``
    when claims could not be grounded, ``HIGH_CAUTION`` when the evidence actively
    contradicts a claim.
    """

    INFO = "info"
    CAUTION = "caution"
    HIGH_CAUTION = "high_caution"


class SafetyAssessment(BaseModel):
    """The guardrail's advisory over a whole result — additive, never mutating it."""

    advisory: Advisory = Field(description="How cautiously to treat the result.")
    disclaimer: str = Field(description="Standing medical-advice disclaimer.")
    notes: list[str] = Field(
        default_factory=list,
        description="Plain-language reasons the advisory level was chosen.",
    )


def assess(result: VerificationResult) -> SafetyAssessment:
    """Judge how cautiously a verification result should be treated.

    The advisory escalates with risk: a ``Contradicted`` claim is the most serious (the
    evidence actively disputes the answer), an ``Unverifiable`` claim warrants caution
    (the answer outran the evidence), and a fully grounded answer is informational. The
    disclaimer is always attached — Aletheia never presents itself as medical advice.
    """
    contradicted = [v for v in result.verdicts if v.verdict is Verdict.CONTRADICTED]
    unverifiable = [v for v in result.verdicts if v.verdict is Verdict.UNVERIFIABLE]

    notes: list[str] = []
    if contradicted:
        advisory = Advisory.HIGH_CAUTION
        notes.append(f"{len(contradicted)} claim(s) are contradicted by the cited evidence.")
    elif unverifiable:
        advisory = Advisory.CAUTION
        notes.append(f"{len(unverifiable)} claim(s) could not be grounded in the evidence.")
    elif not result.verdicts:
        advisory = Advisory.CAUTION
        notes.append("No checkable claims were extracted, so nothing could be verified.")
    else:
        advisory = Advisory.INFO
        notes.append("Every extracted claim is grounded as Supported by the cited evidence.")

    return SafetyAssessment(advisory=advisory, disclaimer=DISCLAIMER, notes=notes)


async def guardrail_node(state: PipelineState) -> PipelineState:
    """Attach a non-mutating :class:`SafetyAssessment` to the assembled result."""
    return {"safety": assess(state["result"])}
