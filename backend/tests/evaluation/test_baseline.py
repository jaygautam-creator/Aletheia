"""Tests for the single-LLM baseline label parsing."""

from __future__ import annotations

import pytest

from aletheia.evaluation.baseline import baseline_supported
from aletheia.evaluation.dataset import DatasetItem, GoldClaim
from aletheia.llm import FakeLLMClient, LLMError

_ITEM = DatasetItem(
    id="t",
    question="q",
    evidence="Some evidence text.",
    candidate_answer="An answer.",
    claims=[
        GoldClaim(text="Claim A.", supported=True),
        GoldClaim(text="Claim B.", supported=False),
    ],
)


async def test_labels_are_parsed_in_order() -> None:
    llm = FakeLLMClient('{"labels": ["Supported", "Unsupported"]}')

    assert await baseline_supported(llm, _ITEM) == [True, False]


async def test_label_casing_is_tolerated() -> None:
    llm = FakeLLMClient('{"labels": ["supported", "UNSUPPORTED"]}')

    assert await baseline_supported(llm, _ITEM) == [True, False]


async def test_length_mismatch_raises() -> None:
    llm = FakeLLMClient('{"labels": ["Supported"]}')

    with pytest.raises(LLMError, match="1 labels for 2 claims"):
        await baseline_supported(llm, _ITEM)
