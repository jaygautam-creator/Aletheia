"""Build the active :class:`LLMClient` from application settings.

This is the single place that knows about concrete providers. Agents depend only on
the abstract client, so swapping providers — or adding a third — is a change here
and nowhere else. When fallback providers are configured the primary is wrapped in a
:class:`FallbackLLMClient` so agents still see one client.

Fallback chain: primary → llm_fallback_provider → llm_fallback_provider_2
Each tier is tried in order; the first success is returned.
"""

from __future__ import annotations

from typing import Literal, assert_never

from aletheia.config import Settings, get_settings
from aletheia.llm.base import LLMClient, LLMConfigurationError
from aletheia.llm.fallback import FallbackLLMClient
from aletheia.llm.gemini import GeminiClient
from aletheia.llm.groq import GroqClient
from aletheia.llm.openrouter import OpenRouterClient

Provider = Literal["gemini", "groq", "openrouter"]

#: Model used for a provider when ``LLM_MODEL`` / ``LLM_FALLBACK_MODEL`` is left unset.
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-3.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "nvidia/nemotron-3-ultra-550b-a55b:free",
}


def build_llm_client(
    settings: Settings | None = None, *, override_key: str | None = None
) -> LLMClient:
    """Return the LLM client selected by ``settings`` (defaults to the process settings).

    When fallback providers are configured, the result is a :class:`FallbackLLMClient`
    that tries the primary first, then the first fallback, then the second fallback.

    ``override_key``, when given, is used for the *primary* provider instead of its
    configured settings key (a user's own BYO key); the fallback chain, if any, still
    uses the server's configured keys. This keeps per-request key overrides additive
    and avoids multiplying the fallback logic's edge cases.

    Raises :class:`LLMConfigurationError` when a selected provider has no API key, or
    when a fallback provider duplicates the one before it.
    """
    settings = settings or get_settings()
    primary = _build_provider(
        settings.llm_provider,
        settings.llm_model or DEFAULT_MODELS[settings.llm_provider],
        settings,
        override_key=override_key,
    )

    chain: list[LLMClient] = [primary]

    for fallback_provider in (settings.llm_fallback_provider, settings.llm_fallback_provider_2):
        if fallback_provider is None:
            break
        prev = chain[-1]
        if fallback_provider == prev.provider:
            raise LLMConfigurationError(
                f"Fallback provider {fallback_provider!r} duplicates the preceding provider; "
                "set it to a different provider or leave it unset."
            )
        chain.append(
            _build_provider(fallback_provider, DEFAULT_MODELS[fallback_provider], settings)
        )

    if len(chain) == 1:
        return chain[0]
    return FallbackLLMClient(chain)


def _build_provider(
    provider: Provider, model: str, settings: Settings, *, override_key: str | None = None
) -> LLMClient:
    """Construct a single concrete provider client, or raise if its key is missing."""
    if override_key is not None:
        if provider == "gemini":
            return GeminiClient(api_key=override_key, model=model)
        if provider == "groq":
            return GroqClient(api_key=override_key, model=model)
        if provider == "openrouter":
            return OpenRouterClient(api_key=override_key, model=model)
        assert_never(provider)

    if provider == "gemini":
        if settings.gemini_api_key is None:
            raise LLMConfigurationError(
                "Gemini was selected but GEMINI_API_KEY is not set. "
                "Add a free key from https://aistudio.google.com/apikey to your .env."
            )
        return GeminiClient(api_key=settings.gemini_api_key.get_secret_value(), model=model)

    if provider == "groq":
        if settings.groq_api_key is None:
            raise LLMConfigurationError(
                "Groq was selected but GROQ_API_KEY is not set. "
                "Add a free key from https://console.groq.com/keys to your .env."
            )
        return GroqClient(api_key=settings.groq_api_key.get_secret_value(), model=model)

    if provider == "openrouter":
        if settings.openrouter_api_key is None:
            raise LLMConfigurationError(
                "OpenRouter was selected but OPENROUTER_API_KEY is not set. "
                "Add a key from https://openrouter.ai/keys to your .env."
            )
        return OpenRouterClient(api_key=settings.openrouter_api_key.get_secret_value(), model=model)

    assert_never(provider)
