"""Tests for the verification verdict contract.

These pin down Aletheia's core invariant: a Supported/Contradicted verdict must
quote evidence, an Unverifiable verdict must not, and a verdict whose quote is not
present in the evidence is downgraded rather than trusted.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aletheia.agents.contracts import ClaimVerdict, Verdict, VerificationResult

EVIDENCE = "The Eiffel Tower was completed in 1889 and stands in Paris, France."


def test_supported_verdict_requires_a_span() -> None:
    with pytest.raises(ValidationError, match="must quote a non-empty evidence span"):
        ClaimVerdict(
            claim="The tower was completed in 1889.",
            verdict=Verdict.SUPPORTED,
            quoted_span=None,
            reasoning="The date is stated.",
        )


def test_contradicted_verdict_requires_a_span() -> None:
    with pytest.raises(ValidationError, match="must quote a non-empty evidence span"):
        ClaimVerdict(
            claim="The tower was completed in 1989.",
            verdict=Verdict.CONTRADICTED,
            quoted_span="   ",  # whitespace-only is treated as empty
            reasoning="The date conflicts.",
        )


def test_unverifiable_verdict_must_not_carry_a_span() -> None:
    with pytest.raises(ValidationError, match="must not carry a quoted span"):
        ClaimVerdict(
            claim="The tower is repainted every seven years.",
            verdict=Verdict.UNVERIFIABLE,
            quoted_span="completed in 1889",
            reasoning="Not addressed by the evidence.",
        )


def test_well_formed_supported_verdict_is_accepted() -> None:
    verdict = ClaimVerdict(
        claim="The tower was completed in 1889.",
        verdict=Verdict.SUPPORTED,
        quoted_span="completed in 1889",
        reasoning="The evidence states the completion year.",
    )

    assert verdict.is_grounded
    assert verdict.is_quote_present_in(EVIDENCE)


def test_unverifiable_verdict_is_always_quote_consistent() -> None:
    verdict = ClaimVerdict(
        claim="The tower is repainted every seven years.",
        verdict=Verdict.UNVERIFIABLE,
        reasoning="The evidence does not address repainting.",
    )

    assert not verdict.is_grounded
    assert verdict.is_quote_present_in(EVIDENCE)


def test_grounded_against_keeps_a_verdict_with_a_real_quote() -> None:
    verdict = ClaimVerdict(
        claim="The tower stands in Paris.",
        verdict=Verdict.SUPPORTED,
        quoted_span="stands in Paris",
        reasoning="The location is stated.",
    )

    assert verdict.grounded_against(EVIDENCE) is verdict


def test_grounded_against_downgrades_a_fabricated_quote() -> None:
    # The model claims support but quotes text that is not in the evidence.
    verdict = ClaimVerdict(
        claim="The tower is 450 metres tall.",
        verdict=Verdict.SUPPORTED,
        quoted_span="450 metres tall",
        reasoning="Hallucinated support.",
    )

    downgraded = verdict.grounded_against(EVIDENCE)

    assert downgraded.verdict is Verdict.UNVERIFIABLE
    assert downgraded.quoted_span is None
    assert downgraded.claim == verdict.claim
    assert "not found verbatim" in downgraded.reasoning


def test_verification_result_summaries() -> None:
    result = VerificationResult(
        query="Tell me about the Eiffel Tower.",
        candidate_answer="It was completed in 1889 in Paris and is 450m tall.",
        verdicts=[
            ClaimVerdict(
                claim="Completed in 1889.",
                verdict=Verdict.SUPPORTED,
                quoted_span="completed in 1889",
                reasoning="Stated.",
            ),
            ClaimVerdict(
                claim="Located in Paris.",
                verdict=Verdict.SUPPORTED,
                quoted_span="stands in Paris",
                reasoning="Stated.",
            ),
            ClaimVerdict(
                claim="It is 450m tall.",
                verdict=Verdict.UNVERIFIABLE,
                reasoning="Height is not addressed.",
            ),
        ],
    )

    assert len(result.supported) == 2
    assert len(result.flagged) == 1
    assert result.has_unsupported_claims
    assert result.support_ratio == pytest.approx(2 / 3)


def test_support_ratio_is_one_when_there_are_no_claims() -> None:
    result = VerificationResult(query="Anything?", candidate_answer="")

    assert result.support_ratio == 1.0
    assert not result.has_unsupported_claims
