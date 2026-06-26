"""Tests for the deterministic FakeLLMClient and the shared generate_json path."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aletheia.llm import FakeLLMClient, LLMError, Message, Role


async def test_constant_response_is_returned_for_every_call() -> None:
    client = FakeLLMClient("hello")

    first = await client.complete([Message.user("a")])
    second = await client.complete([Message.user("b")])

    assert first.text == "hello"
    assert second.text == "hello"
    assert client.call_count == 2


async def test_sequence_responses_are_returned_in_order() -> None:
    client = FakeLLMClient(["one", "two"])

    assert (await client.complete([Message.user("x")])).text == "one"
    assert (await client.complete([Message.user("y")])).text == "two"


async def test_exhausted_sequence_raises() -> None:
    client = FakeLLMClient(["only"])
    await client.complete([Message.user("x")])

    with pytest.raises(LLMError, match="ran out of scripted responses"):
        await client.complete([Message.user("y")])


async def test_router_sees_messages_and_json_flag() -> None:
    def router(messages: Sequence[Message], json_mode: bool) -> str:
        assert json_mode is True
        assert messages[-1].role is Role.USER
        return messages[-1].content.upper()

    client = FakeLLMClient(router)
    response = await client.complete([Message.user("ping")], json_mode=True)

    assert response.text == "PING"


async def test_usage_is_counted_deterministically() -> None:
    client = FakeLLMClient("two words")

    response = await client.complete([Message.user("one two three")])

    assert response.usage is not None
    assert response.usage.prompt_tokens == 3
    assert response.usage.completion_tokens == 2
    assert response.usage.total_tokens == 5


async def test_generate_json_parses_valid_json() -> None:
    client = FakeLLMClient('{"verdict": "Supported", "ok": true}')

    parsed = await client.generate_json([Message.user("judge")])

    assert parsed == {"verdict": "Supported", "ok": True}


async def test_generate_json_raises_on_invalid_json() -> None:
    client = FakeLLMClient("not json at all")

    with pytest.raises(LLMError, match="did not return valid JSON"):
        await client.generate_json([Message.user("judge")])
