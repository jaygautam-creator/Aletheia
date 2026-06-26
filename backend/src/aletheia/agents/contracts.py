"""Verification contracts — the typed verdicts the pipeline is allowed to emit.

The central invariant of Aletheia lives here. A verdict that *affirms or denies*
a claim (``Supported`` / ``Contradicted``) is valid only when it quotes the exact
span of evidence that justifies it. A verdict that cannot point at text is forced
to be ``Unverifiable``. This makes ungrounded verdicts structurally impossible to
emit, which is precisely what defeats the "false agreement" failure mode the
charter describes: agents cannot simply echo one another, they must cite a span.

Two layers enforce the invariant:

* :class:`ClaimVerdict` validates its own *shape* — a grounded verdict must carry
  a non-empty span; an ungrounded one must not.
* :meth:`ClaimVerdict.grounded_against` enforces grounding against *real evidence*
  at the boundary where evidence is available: if the quoted span is not present
  verbatim in the evidence, the verdict is downgraded to ``Unverifiable``. The
  system refuses to affirm a claim on a quote it cannot find.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class Verdict(StrEnum):
    """The judgement the Verifier returns for a single claim."""

    SUPPORTED = "Supported"
    CONTRADICTED = "Contradicted"
    UNVERIFIABLE = "Unverifiable"


#: Verdicts that assert something about the world and therefore require a quoted
#: span of evidence. ``Unverifiable`` is the only verdict that may stand without
#: one — it is the system declining to take a grounded position.
GROUNDED_VERDICTS: frozenset[Verdict] = frozenset({Verdict.SUPPORTED, Verdict.CONTRADICTED})


class ClaimVerdict(BaseModel):
    """A Verifier's judgement of one claim, with the evidence that justifies it."""

    claim: str = Field(min_length=1, description="The atomic claim being judged.")
    verdict: Verdict = Field(description="Supported, Contradicted, or Unverifiable.")
    quoted_span: str | None = Field(
        default=None,
        description=(
            "Exact substring of the evidence justifying the verdict. Required for "
            "Supported/Contradicted; must be absent for Unverifiable."
        ),
    )
    reasoning: str = Field(min_length=1, description="Why this verdict was reached.")

    @model_validator(mode="after")
    def _enforce_grounding_shape(self) -> Self:
        """A grounded verdict must quote a span; an ungrounded one must not."""
        span = (self.quoted_span or "").strip()
        if self.verdict in GROUNDED_VERDICTS and not span:
            raise ValueError(
                f"A {self.verdict.value} verdict must quote a non-empty evidence span."
            )
        if self.verdict is Verdict.UNVERIFIABLE and span:
            raise ValueError("An Unverifiable verdict must not carry a quoted span.")
        return self

    @property
    def is_grounded(self) -> bool:
        """Whether this verdict asserts something that must cite evidence."""
        return self.verdict in GROUNDED_VERDICTS

    def is_quote_present_in(self, evidence: str) -> bool:
        """Return whether the quoted span appears verbatim in ``evidence``.

        Ungrounded (``Unverifiable``) verdicts have nothing to locate and are
        always considered consistent.
        """
        if not self.is_grounded:
            return True
        span = self.quoted_span
        return span is not None and span in evidence

    def grounded_against(self, evidence: str) -> ClaimVerdict:
        """Return a verdict guaranteed to be consistent with ``evidence``.

        If a grounded verdict quotes a span that is not present verbatim in the
        evidence, it is downgraded to ``Unverifiable`` with its span dropped: the
        system will not affirm or contradict a claim on a quote it cannot find.
        Verdicts that are already consistent are returned unchanged.
        """
        if self.is_quote_present_in(evidence):
            return self
        return self.model_copy(
            update={
                "verdict": Verdict.UNVERIFIABLE,
                "quoted_span": None,
                "reasoning": (
                    "Downgraded to Unverifiable: the quoted span was not found "
                    f"verbatim in the evidence. Original reasoning: {self.reasoning}"
                ),
            }
        )


class VerificationResult(BaseModel):
    """The pipeline's output: a candidate answer and its per-claim verdicts."""

    query: str = Field(min_length=1, description="The original user question.")
    candidate_answer: str = Field(description="The Generator's candidate answer.")
    verdicts: list[ClaimVerdict] = Field(
        default_factory=list, description="One grounded verdict per extracted claim."
    )

    @property
    def supported(self) -> list[ClaimVerdict]:
        """Claims the Verifier could ground as Supported."""
        return [v for v in self.verdicts if v.verdict is Verdict.SUPPORTED]

    @property
    def flagged(self) -> list[ClaimVerdict]:
        """Claims that are Contradicted or Unverifiable — the ones to surface."""
        return [v for v in self.verdicts if v.verdict is not Verdict.SUPPORTED]

    @property
    def has_unsupported_claims(self) -> bool:
        """Whether any claim failed to be grounded as Supported."""
        return bool(self.flagged)

    @property
    def support_ratio(self) -> float:
        """Fraction of claims grounded as Supported, in ``[0.0, 1.0]``.

        A provisional signal for Phase 1 — deliberately *not* called "confidence",
        which implies the calibration introduced by the Phase 3 evaluation harness.
        Returns ``1.0`` when there are no claims (nothing was left unsupported).
        """
        if not self.verdicts:
            return 1.0
        return len(self.supported) / len(self.verdicts)
