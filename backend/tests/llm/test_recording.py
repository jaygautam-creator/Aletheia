"""Tests for the recording LLM client decorator.

It wraps a delegate (here the deterministic :class:`FakeLLMClient`), captures each call's
token usage and latency, and returns the delegate's output unchanged.
"""

from __future__ import annotations

from aletheia.llm import FakeLLMClient, Message, RecordingLLMClient


async def test_records_usage_and_latency_per_call() -> None:
    client = RecordingLLMClient(FakeLLMClient(["one two three"]))

    response = await client.complete([Message.user("hello world")])

    assert response.text == "one two three"  # the delegate's output is unchanged
    assert len(client.records) == 1
    record = client.records[0]
    assert record.prompt_tokens == 2  # "hello world"
    assert record.completion_tokens == 3  # "one two three"
    assert record.total_tokens == 5
    assert record.latency_s >= 0.0


def test_provider_and_model_reflect_the_delegate() -> None:
    client = RecordingLLMClient(FakeLLMClient("x", model="fake-7"))

    assert client.provider == "fake"
    assert client.model == "fake-7"


async def test_usage_is_captured_through_generate_json() -> None:
    # Agents call generate_json, which discards usage; wrapping complete still records it.
    client = RecordingLLMClient(FakeLLMClient(['{"ok": true}']))

    parsed = await client.generate_json([Message.user("question")])

    assert parsed == {"ok": True}
    assert len(client.records) == 1
    assert client.records[0].completion_tokens == 2  # '{"ok": true}' -> two whitespace tokens


async def test_aggregates_usage_and_resets() -> None:
    client = RecordingLLMClient(FakeLLMClient(["a a", "b b b"]))

    await client.complete([Message.user("p p p")])
    await client.complete([Message.user("q")])

    assert [usage.total_tokens for usage in client.usages] == [3 + 2, 1 + 3]
    assert client.total_usage.prompt_tokens == 4  # "p p p" + "q"
    assert client.total_usage.completion_tokens == 5  # "a a" + "b b b"

    client.reset()
    assert client.records == []
    assert client.total_usage.total_tokens == 0
