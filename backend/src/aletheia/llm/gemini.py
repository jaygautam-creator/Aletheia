"""Google Gemini adapter.

Gemini is Aletheia's default provider: its free tier offers the strongest grounded
reasoning, which is exactly what the Verifier needs to judge claims against evidence.
This adapter normalises Gemini's request/response shape onto the common interface and
retries transient server errors with bounded exponential backoff.
"""

from __future__ import annotations

from collections.abc import Sequence

from google import genai
from google.genai import types
from google.genai.errors import APIError, ServerError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from aletheia.llm.base import LLMClient, LLMError, LLMResponse, Message, Role, TokenUsage

# Gemini speaks "user" and "model"; system text goes in a dedicated field, not a turn.
_GEMINI_ROLE: dict[Role, str] = {Role.USER: "user", Role.ASSISTANT: "model"}

_HTTP_TOO_MANY_REQUESTS = 429


def _is_transient(exc: BaseException) -> bool:
    """Retry server errors (5xx) and rate limits (429); fail fast on other 4xx."""
    if isinstance(exc, ServerError):
        return True
    return isinstance(exc, APIError) and getattr(exc, "code", None) == _HTTP_TOO_MANY_REQUESTS


class GeminiClient(LLMClient):
    """An :class:`LLMClient` backed by the Google Gemini API."""

    provider = "gemini"

    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(model=model)
        self._client = genai.Client(api_key=api_key)

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        system_instruction = "\n\n".join(m.content for m in messages if m.role is Role.SYSTEM)
        contents = [
            types.Content(role=_GEMINI_ROLE[m.role], parts=[types.Part(text=m.content)])
            for m in messages
            if m.role is not Role.SYSTEM
        ]
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction or None,
            response_mime_type="application/json" if json_mode else None,
        )

        try:
            response = await self._generate(contents, config)
        except Exception as exc:  # normalise any provider failure into LLMError
            raise LLMError(f"Gemini request failed: {exc}") from exc

        if response.text is None:
            raise LLMError("Gemini returned an empty response (no text candidate).")

        return LLMResponse(text=response.text, model=self.model, usage=_usage_of(response))

    @retry(
        reraise=True,
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
    )
    async def _generate(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse:
        return await self._client.aio.models.generate_content(
            model=self.model, contents=contents, config=config
        )


def _usage_of(response: types.GenerateContentResponse) -> TokenUsage | None:
    meta = response.usage_metadata
    if meta is None:
        return None
    return TokenUsage(
        prompt_tokens=meta.prompt_token_count or 0,
        completion_tokens=meta.candidates_token_count or 0,
    )
