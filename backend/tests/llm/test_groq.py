"""Tests for the Groq client's retry policy — entirely offline.

The policy under test exists because a benchmark run must survive two transient
Groq failures without falling over to another provider (which would contaminate
a paired comparison): JSON-mode validation failures (400 ``json_validate_failed``,
usually fixed by resampling) and per-minute rate limits whose ``retry-after`` is
longer than a blind exponential backoff would wait.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from groq import BadRequestError, RateLimitError
from groq.types.chat import ChatCompletion, ChatCompletionMessage
from groq.types.chat.chat_completion import Choice
from groq.types.completion_usage import CompletionUsage

from aletheia.llm.base import LLMError, Message, Role
from aletheia.llm.groq import (
    _MAX_RETRY_AFTER_SECONDS,
    GroqClient,
    _is_json_validation_failure,
    _is_retryable,
    _RetryAfterOrExponential,
)

_REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _rate_limit_error(headers: dict[str, str]) -> RateLimitError:
    response = httpx.Response(429, headers=headers, request=_REQUEST)
    return RateLimitError("rate limited", response=response, body=None)


def _json_validate_error() -> BadRequestError:
    body = {"error": {"code": "json_validate_failed", "message": "Failed to generate JSON."}}
    response = httpx.Response(400, request=_REQUEST)
    return BadRequestError(f"Error code: 400 - {body}", response=response, body=body)


def _wait_state(exc: BaseException | None) -> Any:
    """A minimal stand-in for tenacity's RetryCallState: just the outcome exception."""
    outcome = None if exc is None else SimpleNamespace(exception=lambda: exc)
    return SimpleNamespace(outcome=outcome, attempt_number=1)


def _completion(text: str) -> ChatCompletion:
    return ChatCompletion(
        id="cmpl-1",
        model="llama-3.1-8b-instant",
        object="chat.completion",
        created=0,
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message=ChatCompletionMessage(role="assistant", content=text),
            )
        ],
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def test_json_validation_failure_is_transient() -> None:
    assert _is_json_validation_failure(_json_validate_error()) is True
    assert _is_retryable(_json_validate_error()) is True


def test_other_bad_requests_are_not_retried() -> None:
    response = httpx.Response(400, request=_REQUEST)
    other = BadRequestError("model_decommissioned", response=response, body=None)
    assert _is_retryable(other) is False


def test_wait_honors_the_servers_retry_after() -> None:
    wait = _RetryAfterOrExponential()
    assert wait(_wait_state(_rate_limit_error({"retry-after": "9"}))) == pytest.approx(9.5)


def test_wait_caps_an_excessive_retry_after() -> None:
    # A daily-cap 429 can ask for hours; waiting that long inside a call is worse
    # than failing fast, so the honored pause is capped.
    wait = _RetryAfterOrExponential()
    assert wait(_wait_state(_rate_limit_error({"retry-after": "3600"}))) == pytest.approx(
        _MAX_RETRY_AFTER_SECONDS
    )


def test_wait_falls_back_to_exponential_without_retry_after() -> None:
    wait = _RetryAfterOrExponential()
    # No header, an unparseable header, and a non-429 all take the exponential path,
    # whose first wait is well under a second.
    for exc in (
        _rate_limit_error({}),
        _rate_limit_error({"retry-after": "soon"}),
        _json_validate_error(),
    ):
        assert 0 < wait(_wait_state(exc)) <= 8


async def test_json_validation_failure_is_retried_until_it_parses() -> None:
    client = GroqClient(api_key="test-key", model="llama-3.1-8b-instant")
    calls = 0

    async def create(**kwargs: Any) -> ChatCompletion:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _json_validate_error()
        return _completion('{"ok": true}')

    client._client.chat.completions.create = create  # type: ignore[method-assign]

    response = await client.complete([Message(role=Role.USER, content="hi")], json_mode=True)

    assert calls == 2
    assert response.text == '{"ok": true}'


async def test_a_persistent_failure_still_raises_llm_error() -> None:
    client = GroqClient(api_key="test-key", model="llama-3.1-8b-instant")

    async def create(**kwargs: Any) -> ChatCompletion:
        raise _json_validate_error()

    client._client.chat.completions.create = create  # type: ignore[method-assign]

    with pytest.raises(LLMError, match="Groq request failed"):
        await client.complete([Message(role=Role.USER, content="hi")])
