"""Tests for the Verifier node and its two grounding defences."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from aletheia.agents.contracts import ClaimVerdict, Verdict
from aletheia.agents.state import PipelineState
from aletheia.agents.verifier import make_verifier_node
from aletheia.llm import FakeLLMClient
from aletheia.llm.base import LLMClient, LLMResponse, Message, TokenUsage

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


async def test_verdicts_line_up_with_claims_in_order() -> None:
    # With claims verified concurrently, verdicts must still map back to the right claim.
    # Route each call by the claim in its prompt so a mis-zip would be caught.
    # Route on a token unique to each claim (the evidence mentions both prizes, so keying
    # on "physics"/"chemistry" would be ambiguous — "alpha"/"beta" appear only in claims).
    def supported(span: str) -> str:
        return f'{{"verdict": "Supported", "quoted_span": "{span}", "reasoning": "r"}}'

    def router(messages: Sequence[Message], _json_mode: bool) -> str:
        text = " ".join(m.content for m in messages).lower()
        if "alpha" in text:
            return supported("Physics in 1903")
        if "beta" in text:
            return supported("Chemistry in 1911")
        return '{"verdict": "Unverifiable", "quoted_span": null, "reasoning": "x"}'

    node = make_verifier_node(FakeLLMClient(router))
    state: PipelineState = {
        "evidence": EVIDENCE,
        "claims": ["alpha claim", "beta claim"],
    }
    out = await node(state)
    verdicts = out["verdicts"]

    assert [v.claim for v in verdicts] == ["alpha claim", "beta claim"]
    assert verdicts[0].quoted_span == "Physics in 1903"
    assert verdicts[1].quoted_span == "Chemistry in 1911"


class _BarrierClient(LLMClient):
    """An LLM client whose calls only complete once ALL of them are in flight.

    Every ``complete`` waits on a shared barrier sized to the number of claims, so the
    node returns only if the calls run concurrently. A sequential loop would block the
    first call at the barrier forever — surfaced here as a timeout.
    """

    provider = "barrier"

    def __init__(self, parties: int) -> None:
        super().__init__(model="barrier-1")
        self._barrier = asyncio.Barrier(parties)

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        await self._barrier.wait()
        return LLMResponse(
            text='{"verdict": "Unverifiable", "quoted_span": null, "reasoning": "ok"}',
            model=self.model,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
        )


async def test_claims_are_verified_concurrently() -> None:
    claims = [f"claim {i}" for i in range(4)]
    node = make_verifier_node(_BarrierClient(len(claims)))
    state: PipelineState = {"evidence": EVIDENCE, "claims": claims}

    # If verification were sequential the barrier would deadlock; wait_for keeps the
    # test from hanging and asserts concurrency by completing well within the timeout.
    out = await asyncio.wait_for(node(state), timeout=2.0)

    assert len(out["verdicts"]) == len(claims)
