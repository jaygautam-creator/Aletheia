"""End-to-end test of the verification graph on a planted unsupported claim.

This is the thesis in miniature: the Generator splits the answer into claims, the
Verifier grounds each against the evidence, and the one claim that has no supporting
span is flagged rather than waved through — even though the model "asserted" support
for it with a fabricated quote.
"""

from __future__ import annotations

from aletheia.agents import Verdict, VerificationPipeline
from aletheia.llm import FakeLLMClient

EVIDENCE = "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911."
ANSWER = "Marie Curie won the 1903 Nobel Prize in Physics. She also discovered penicillin."

# One generator call, then one verifier call per claim, in claim order.
_SCRIPT = [
    '{"claims": ["Marie Curie won the 1903 Nobel Prize in Physics.", '
    '"Marie Curie discovered penicillin."]}',
    '{"verdict": "Supported", "quoted_span": "Nobel Prize in Physics in 1903", '
    '"reasoning": "Stated by the evidence."}',
    # The planted claim: the model fabricates a quote to "support" it.
    '{"verdict": "Supported", "quoted_span": "discovered penicillin", '
    '"reasoning": "Fabricated support."}',
]


async def test_pipeline_catches_the_unsupported_claim() -> None:
    llm = FakeLLMClient(_SCRIPT)
    pipeline = VerificationPipeline(llm)

    result = await pipeline.run(
        query="What is Marie Curie known for?",
        evidence=EVIDENCE,
        candidate_answer=ANSWER,
    )

    assert llm.call_count == 3
    assert result.candidate_answer == ANSWER
    assert len(result.verdicts) == 2

    # First claim is genuinely grounded; second is caught despite the fabricated quote.
    assert result.verdicts[0].verdict is Verdict.SUPPORTED
    assert result.verdicts[1].verdict is Verdict.UNVERIFIABLE
    assert result.verdicts[1].quoted_span is None

    assert result.has_unsupported_claims
    assert [v.claim for v in result.flagged] == ["Marie Curie discovered penicillin."]
    assert result.support_ratio == 0.5
