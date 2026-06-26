"""Tests for the Verifier node and its two grounding defences."""

from __future__ import annotations

from aletheia.agents.contracts import ClaimVerdict, Verdict
from aletheia.agents.state import PipelineState
from aletheia.agents.verifier import make_verifier_node
from aletheia.llm import FakeLLMClient

EVIDENCE = "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911."


async def _verify_one(response: str, claim: str = "a claim") -> ClaimVerdict:
    node = make_verifier_node(FakeLLMClient(response))
    state: PipelineState = {"evidence": EVIDENCE, "claims": [claim]}
    out = await node(state)
    return out["verdicts"][0]


async def test_supported_with_a_real_span_is_kept() -> None:
    verdict = await _verify_one(
        '{"verdict": "Supported", "quoted_span": "Nobel Prize in Physics in 1903", '
        '"reasoning": "Stated."}'
    )
    assert verdict.verdict is Verdict.SUPPORTED
    assert verdict.quoted_span == "Nobel Prize in Physics in 1903"


async def test_contradicted_with_a_real_span_is_kept() -> None:
    verdict = await _verify_one(
        '{"verdict": "Contradicted", "quoted_span": "in Chemistry in 1911", '
        '"reasoning": "Conflicts."}'
    )
    assert verdict.verdict is Verdict.CONTRADICTED


async def test_fabricated_span_is_downgraded_to_unverifiable() -> None:
    # The model claims support but quotes text absent from the evidence.
    verdict = await _verify_one(
        '{"verdict": "Supported", "quoted_span": "discovered penicillin", '
        '"reasoning": "Hallucinated support."}'
    )
    assert verdict.verdict is Verdict.UNVERIFIABLE
    assert verdict.quoted_span is None
    assert "not found verbatim" in verdict.reasoning


async def test_grounded_verdict_without_a_span_is_downgraded() -> None:
    verdict = await _verify_one(
        '{"verdict": "Supported", "quoted_span": null, "reasoning": "No quote."}'
    )
    assert verdict.verdict is Verdict.UNVERIFIABLE
    assert "quoted no span" in verdict.reasoning


async def test_unverifiable_passes_through() -> None:
    verdict = await _verify_one(
        '{"verdict": "Unverifiable", "quoted_span": null, "reasoning": "Not addressed."}'
    )
    assert verdict.verdict is Verdict.UNVERIFIABLE


async def test_verdict_casing_is_normalised() -> None:
    verdict = await _verify_one(
        '{"verdict": "supported", "quoted_span": "in Chemistry in 1911", '
        '"reasoning": "Lowercase verdict."}'
    )
    assert verdict.verdict is Verdict.SUPPORTED
