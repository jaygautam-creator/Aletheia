"""Guards on the Verifier prompts' fairness contract (EVALUATION.md §5).

The grounded prompt and the ablation prompt must differ *only* in the span discipline,
or the H2 ablation stops isolating what evidence-grounding contributes. These tests pin
that split — including that the span-sufficiency test lives only on the grounded side —
so an accidental edit to either prompt is caught in CI rather than silently invalidating
the comparison.
"""

from __future__ import annotations

from aletheia.agents.prompts import verify_messages, verify_ungrounded_messages

GROUNDED = verify_messages("a claim", "some evidence")[0].content
UNGROUNDED = verify_ungrounded_messages("a claim", "some evidence")[0].content


def test_grounded_prompt_requires_a_verbatim_span() -> None:
    low = GROUNDED.lower()
    assert "quote" in low
    assert "verbatim" in low


def test_grounded_prompt_carries_the_two_sided_sufficiency_test() -> None:
    low = GROUNDED.lower()
    assert "sufficiency test" in low
    assert "settles this exact claim" in low
    # Cuts false-grounding: a merely-topical span is not enough.
    assert "same topic" in low
    # Cuts over-abstention: a decisive span must not be downgraded out of caution.
    assert "do not retreat to unverifiable" in low
    # Cuts over-abstention on paraphrased claims: wording need not match the span.
    assert "judge meaning, not wording" in low


def test_ungrounded_prompt_has_no_span_discipline() -> None:
    low = UNGROUNDED.lower()
    for token in ("quote", "span", "verbatim", "sufficiency test"):
        assert token not in low, f"ablation prompt leaked span discipline: {token!r}"


def test_both_share_the_same_opener_and_verdicts() -> None:
    opener = "You are a strict verification critic."
    assert GROUNDED.startswith(opener)
    assert UNGROUNDED.startswith(opener)
    for verdict in ("Supported", "Contradicted", "Unverifiable"):
        assert verdict in GROUNDED
        assert verdict in UNGROUNDED
