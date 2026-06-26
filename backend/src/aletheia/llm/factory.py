"""Build the active :class:`LLMClient` from application settings.

This is the single place that knows about concrete providers. Agents depend only on
the abstract client, so swapping Gemini for Groq — or adding a third provider — is a
change here and nowhere else.
"""

from __future__ import annotations

from typing import assert_never

from aletheia.config import Settings, get_settings
from aletheia.llm.base import LLMClient, LLMConfigurationError
from aletheia.llm.gemini import GeminiClient
from aletheia.llm.groq import GroqClient

#: Model used for a provider when ``LLM_MODEL`` is left unset.
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
}


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Return the LLM client selected by ``settings`` (defaults to the process settings).

    Raises :class:`LLMConfigurationError` when the chosen provider has no API key.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS[provider]

    if provider == "gemini":
        if settings.gemini_api_key is None:
            raise LLMConfigurationError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                "Add a free key from https://aistudio.google.com/apikey to your .env."
            )
        return GeminiClient(api_key=settings.gemini_api_key.get_secret_value(), model=model)

    if provider == "groq":
        if settings.groq_api_key is None:
            raise LLMConfigurationError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add a free key from https://console.groq.com/keys to your .env."
            )
        return GroqClient(api_key=settings.groq_api_key.get_secret_value(), model=model)

    assert_never(provider)
