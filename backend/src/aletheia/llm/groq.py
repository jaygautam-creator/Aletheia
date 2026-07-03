"""Groq adapter.

Groq is wired as a first-class alternative to Gemini. Its strength is throughput:
the Phase 3 evaluation harness runs each configuration many times, and Groq's very
fast inference makes those sweeps cheap — as well as giving the paper a second,
independent provider for a cross-model comparison.
"""

from __future__ import annotations

from collections.abc import Sequence

from groq import APIConnectionError, APITimeoutError, AsyncGroq, InternalServerError, RateLimitError
from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.chat.completion_create_params import ResponseFormatResponseFormatJsonObject
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from aletheia.llm.base import LLMClient, LLMError, LLMResponse, Message, Role, TokenUsage

_JSON_OBJECT = ResponseFormatResponseFormatJsonObject(type="json_object")

# Groq errors worth retrying: connectivity, timeouts, rate limits, and 5xx.
_TRANSIENT = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


def _to_param(message: Message) -> ChatCompletionMessageParam:
    if message.role is Role.SYSTEM:
        return ChatCompletionSystemMessageParam(role="system", content=message.content)
    if message.role is Role.ASSISTANT:
        return ChatCompletionAssistantMessageParam(role="assistant", content=message.content)
    return ChatCompletionUserMessageParam(role="user", content=message.content)


class GroqClient(LLMClient):
    """An :class:`LLMClient` backed by the Groq API (OpenAI-compatible chat)."""

    provider = "groq"

    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(model=model)
        # max_retries=0: retrying is owned by the tenacity policy on _create. Leaving
        # the SDK's default (2) multiplies the attempts (3x3) and, on an unreachable
        # network, stalls failover for ~45s instead of ~15s.
        self._client = AsyncGroq(api_key=api_key, max_retries=0)

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        params = [_to_param(m) for m in messages]

        try:
            completion = await self._create(params, temperature=temperature, json_mode=json_mode)
        except Exception as exc:  # normalise any provider failure into LLMError
            raise LLMError(f"Groq request failed: {exc}") from exc

        content = completion.choices[0].message.content
        if content is None:
            raise LLMError("Groq returned an empty response (no message content).")

        usage = None
        if completion.usage is not None:
            usage = TokenUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
            )
        return LLMResponse(text=content, model=self.model, usage=usage)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
    )
    async def _create(
        self,
        params: list[ChatCompletionMessageParam],
        *,
        temperature: float,
        json_mode: bool,
    ) -> ChatCompletion:
        return await self._client.chat.completions.create(
            model=self.model,
            messages=params,
            temperature=temperature,
            response_format=_JSON_OBJECT if json_mode else None,
        )
