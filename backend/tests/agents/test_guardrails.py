"""Tests for the output guardrail — the advisory + disclaimer layer.

These are pure functions over a :class:`VerificationResult`; the guardrail never mutates
the result, so the tests assert only on the assessment it returns.
"""

from __future__ import annotations

from aletheia.agents.contracts import ClaimVerdict, Verdict, VerificationResult
from aletheia.agents.guardrails import DISCLAIMER, Advisory, assess


def _result(*verdicts: ClaimVerdict) -> VerificationResult:
    return VerificationResult(query="q", candidate_answer="an answer", verdicts=list(verdicts))


def _supported() -> ClaimVerdict:
    return ClaimVerdict(claim="c", verdict=Verdict.SUPPORTED, quoted_span="span", reasoning="r")


def _contradicted() -> ClaimVerdict:
    return ClaimVerdict(claim="c", verdict=Verdict.CONTRADICTED, quoted_span="span", reasoning="r")


def _unverifiable() -> ClaimVerdict:
    return ClaimVerdict(claim="c", verdict=Verdict.UNVERIFIABLE, reasoning="r")


def test_all_supported_is_informational() -> None:
    assessment = assess(_result(_supported(), _supported()))

    assert assessment.advisory is Advisory.INFO
    assert assessment.notes


def test_an_unverifiable_claim_warrants_caution() -> None:
    assessment = assess(_result(_supported(), _unverifiable()))

    assert assessment.advisory is Advisory.CAUTION


def test_a_contradicted_claim_is_high_caution_even_amid_supported_ones() -> None:
    # Contradiction is the most serious signal and wins over supported/unverifiable.
    assessment = assess(_result(_supported(), _unverifiable(), _contradicted()))

    assert assessment.advisory is Advisory.HIGH_CAUTION
    assert "contradicted" in assessment.notes[0].lower()


def test_no_verdicts_warrants_caution() -> None:
    assessment = assess(_result())

    assert assessment.advisory is Advisory.CAUTION


def test_disclaimer_is_always_attached_and_disclaims_medical_advice() -> None:
    assessment = assess(_result(_supported()))

    assert assessment.disclaimer == DISCLAIMER
    assert "medical advice" in DISCLAIMER.lower()


def test_assess_does_not_mutate_the_result() -> None:
    result = _result(_supported(), _unverifiable())
    before = result.model_dump()

    assess(result)

    assert result.model_dump() == before
