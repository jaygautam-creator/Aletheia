"""Tests for the fail-over LLM client.

It wraps an ordered chain of clients (here deterministic :class:`FakeLLMClient`s and a
small always-failing stub), returns the first success, and only surfaces a failure when
every provider in the chain is exhausted. No network is touched.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aletheia.llm import FakeLLMClient, FallbackLLMClient, Message
from aletheia.llm.base import LLMClient, LLMError, LLMResponse


class _FailingClient(LLMClient):
    """A client whose every call raises :class:`LLMError` — a stand-in for an outage."""

    provider = "boom"

    def __init__(self, *, model: str = "down-1") -> None:
        super().__init__(model=model)
        self.call_count = 0

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.call_count += 1
        raise LLMError("provider unavailable")


def test_empty_chain_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        FallbackLLMClient([])


def test_provider_and_model_reflect_the_primary() -> None:
    client = FallbackLLMClient(
        [FakeLLMClient("ok", model="primary-9"), FakeLLMClient("backup", model="fallback-9")]
    )

    assert client.provider == "fake"
    assert client.model == "primary-9"


async def test_uses_the_primary_when_it_succeeds() -> None:
    primary = FakeLLMClient("from primary")
    fallback = FakeLLMClient("from fallback")
    client = FallbackLLMClient([primary, fallback])

    response = await client.complete([Message.user("hi")])

    assert response.text == "from primary"
    assert primary.call_count == 1
    assert fallback.call_count == 0  # the fallback is never touched


async def test_falls_over_to_the_next_provider_on_failure() -> None:
    down = _FailingClient()
    backup = FakeLLMClient("recovered")
    client = FallbackLLMClient([down, backup])

    response = await client.complete([Message.user("hi")])

    assert response.text == "recovered"
    assert down.call_count == 1  # the primary was tried first
    # The answering model is the fallback's, so cost accounting attributes it correctly.
    assert response.model == "fake-1"


async def test_raises_the_last_error_when_the_whole_chain_is_exhausted() -> None:
    first = _FailingClient(model="down-a")
    second = _FailingClient(model="down-b")
    client = FallbackLLMClient([first, second])

    with pytest.raises(LLMError, match="provider unavailable"):
        await client.complete([Message.user("hi")])

    assert first.call_count == 1
    assert second.call_count == 1  # every provider was attempted


async def test_generate_json_also_fails_over() -> None:
    # A provider that returns unparseable JSON raises LLMError inside generate_json;
    # the fallback should still recover with valid JSON.
    bad_json = FakeLLMClient("not json at all")
    good_json = FakeLLMClient('{"ok": true}')
    client = FallbackLLMClient([bad_json, good_json])

    parsed = await client.generate_json([Message.user("question")])

    assert parsed == {"ok": True}
    assert bad_json.call_count == 1
    assert good_json.call_count == 1
