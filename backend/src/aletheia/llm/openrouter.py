"""OpenRouter adapter — third-tier fallback provider.

OpenRouter exposes an OpenAI-compatible chat-completions endpoint that routes
requests across hundreds of models. We use it here as a last-resort fallback
(after Groq and Gemini are both exhausted) so the pipeline can always make
progress even when both primary providers hit their free-tier limits.

The implementation is intentionally minimal: we POST JSON with ``httpx`` directly
rather than pulling in the openai SDK, since ``httpx`` is already a project
dependency. Transient failures (connection errors, 429, 5xx) are retried with
bounded exponential backoff before the error is promoted to an :class:`LLMError`
and the :class:`~aletheia.llm.fallback.FallbackLLMClient` sees it.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from aletheia.llm.base import LLMClient, LLMError, LLMResponse, Message, Role, TokenUsage

_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


def _to_dict(message: Message) -> dict[str, str]:
    role = {Role.SYSTEM: "system", Role.USER: "user", Role.ASSISTANT: "assistant"}[message.role]
    return {"role": role, "content": message.content}


class OpenRouterClient(LLMClient):
    """An :class:`LLMClient` backed by the OpenRouter API."""

    provider = "openrouter"

    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(model=model)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jaygautam-creator/Aletheia",
            "X-Title": "Aletheia",
        }

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": [_to_dict(m) for m in messages],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            data = await self._post(payload)
        except Exception as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc

        try:
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"OpenRouter returned an unexpected response shape: {data}") from exc

        if not content:
            raise LLMError("OpenRouter returned an empty response (no message content).")

        usage = None
        if raw_usage := data.get("usage"):
            usage = TokenUsage(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
            )
        return LLMResponse(text=content, model=self.model, usage=usage)

    @retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
    )
    async def _post(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(_BASE_URL, headers=self._headers, json=payload)
        if response.status_code in _RETRYABLE_STATUS:
            raise LLMError(f"OpenRouter request failed: {response.status_code} {response.text}")
        response.raise_for_status()
        return response.json()
