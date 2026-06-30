"""Build the active :class:`LLMClient` from application settings.

This is the single place that knows about concrete providers. Agents depend only on
the abstract client, so swapping Gemini for Groq — or adding a third provider — is a
change here and nowhere else. When a fallback provider is configured, the primary is
wrapped in a :class:`FallbackLLMClient` so the agents still see one client.
"""

from __future__ import annotations

from typing import Literal, assert_never

from aletheia.config import Settings, get_settings
from aletheia.llm.base import LLMClient, LLMConfigurationError
from aletheia.llm.fallback import FallbackLLMClient
from aletheia.llm.gemini import GeminiClient
from aletheia.llm.groq import GroqClient

Provider = Literal["gemini", "groq"]

#: Model used for a provider when ``LLM_MODEL`` is left unset.
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
}


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Return the LLM client selected by ``settings`` (defaults to the process settings).

    When ``llm_fallback_provider`` is set, the result is a :class:`FallbackLLMClient`
    that tries the primary first and fails over to the fallback (on its default model).

    Raises :class:`LLMConfigurationError` when a selected provider has no API key, or
    when the fallback provider duplicates the primary.
    """
    settings = settings or get_settings()
    primary = _build_provider(
        settings.llm_provider,
        settings.llm_model or DEFAULT_MODELS[settings.llm_provider],
        settings,
    )

    fallback_provider = settings.llm_fallback_provider
    if fallback_provider is None:
        return primary
    if fallback_provider == settings.llm_provider:
        raise LLMConfigurationError(
            f"LLM_FALLBACK_PROVIDER={fallback_provider} duplicates LLM_PROVIDER; "
            "set it to a different provider or leave it unset."
        )

    fallback = _build_provider(fallback_provider, DEFAULT_MODELS[fallback_provider], settings)
    return FallbackLLMClient([primary, fallback])


def _build_provider(provider: Provider, model: str, settings: Settings) -> LLMClient:
    """Construct a single concrete provider client, or raise if its key is missing."""
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

    assert_never(provider)
