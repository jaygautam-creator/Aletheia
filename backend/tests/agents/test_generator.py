"""Tests for the Generator node."""

from __future__ import annotations

import pytest

from aletheia.agents.generator import make_generator_node
from aletheia.agents.state import PipelineState
from aletheia.llm import FakeLLMClient, LLMError


async def test_decomposes_a_supplied_answer_without_changing_it() -> None:
    llm = FakeLLMClient('{"claims": ["Claim one.", "Claim two."]}')
    node = make_generator_node(llm)
    state: PipelineState = {
        "query": "Tell me about X.",
        "candidate_answer": "X is a thing. X does something.",
    }

    out = await node(state)

    assert out["candidate_answer"] == "X is a thing. X does something."
    assert out["claims"] == ["Claim one.", "Claim two."]


async def test_generates_an_answer_when_none_is_supplied() -> None:
    llm = FakeLLMClient('{"answer": "X is blue.", "claims": ["X is blue."]}')
    node = make_generator_node(llm)

    out = await node({"query": "What colour is X?"})

    assert out["candidate_answer"] == "X is blue."
    assert out["claims"] == ["X is blue."]


async def test_blank_claims_are_dropped() -> None:
    llm = FakeLLMClient('{"claims": ["Real claim.", "  ", 42]}')
    node = make_generator_node(llm)

    out = await node({"query": "q", "candidate_answer": "a"})

    assert out["claims"] == ["Real claim."]


async def test_no_usable_claims_raises() -> None:
    llm = FakeLLMClient('{"claims": []}')
    node = make_generator_node(llm)

    with pytest.raises(LLMError, match="no usable claims"):
        await node({"query": "q", "candidate_answer": "a"})
