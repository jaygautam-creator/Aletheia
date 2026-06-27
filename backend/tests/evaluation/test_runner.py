"""End-to-end test of the comparison runner with a scripted model.

The fake routes by prompt: the baseline rubber-stamps every claim, while the grounded
verifier fabricates a quote for the planted claim — which the grounding check then
downgrades. The runner must turn this into the expected score gap.
"""

from __future__ import annotations

from collections.abc import Sequence

from aletheia.evaluation.dataset import DatasetItem, GoldClaim
from aletheia.evaluation.phase1 import run_comparison
from aletheia.llm import FakeLLMClient, Message

# "fact one" appears in the evidence; "fact three" does not.
_ITEM = DatasetItem(
    id="t",
    question="What are the facts?",
    evidence="The report states fact one and fact two.",
    candidate_answer="The report establishes fact one and fact three.",
    claims=[
        GoldClaim(text="The report states fact one.", supported=True),
        GoldClaim(text="The report states fact three.", supported=False),
    ],
)


def _router(messages: Sequence[Message], json_mode: bool) -> str:
    system = messages[0].content
    user = messages[-1].content
    if "labels" in system:  # the single-LLM baseline call
        return '{"labels": ["Supported", "Supported"]}'
    # "fact three" appears only in the planted claim, never in the evidence, so it
    # cleanly distinguishes the two verifier calls.
    if "fact three" in user:  # planted claim: "supported" with a fabricated quote
        return '{"verdict": "Supported", "quoted_span": "fact three", "reasoning": "Fabricated."}'
    return '{"verdict": "Supported", "quoted_span": "fact one", "reasoning": "Stated."}'


async def test_grounded_catches_what_the_baseline_misses() -> None:
    llm = FakeLLMClient(_router)

    result = await run_comparison(llm, [_ITEM])

    # The baseline rubber-stamps the planted claim; the grounded verifier catches it.
    assert result.baseline.catch_rate == 0.0
    assert result.grounded.catch_rate == 1.0
    assert result.grounded.false_flags == 0
    assert result.grounded.accuracy == 1.0
    assert "Catch rate" in result.render()
