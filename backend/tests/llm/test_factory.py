"""Tests for provider selection in build_llm_client.

These never touch the network: constructing a provider client only configures an SDK
object; no request is made until ``complete`` is called.
"""

from __future__ import annotations

import pytest

from aletheia.config import Settings
from aletheia.llm import LLMConfigurationError, build_llm_client
from aletheia.llm.gemini import GeminiClient
from aletheia.llm.groq import GroqClient


def _settings(**overrides: object) -> Settings:
    """Build hermetic settings: ignore any local .env and OS-provided keys."""
    base: dict[str, object] = {
        "gemini_api_key": None,
        "groq_api_key": None,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_gemini_without_key_raises() -> None:
    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        build_llm_client(_settings(llm_provider="gemini"))


def test_groq_without_key_raises() -> None:
    with pytest.raises(LLMConfigurationError, match="GROQ_API_KEY"):
        build_llm_client(_settings(llm_provider="groq"))


def test_gemini_with_key_uses_default_model() -> None:
    client = build_llm_client(_settings(llm_provider="gemini", gemini_api_key="test-key"))

    assert isinstance(client, GeminiClient)
    assert client.provider == "gemini"
    assert client.model == "gemini-2.0-flash"


def test_groq_with_key_uses_default_model() -> None:
    client = build_llm_client(_settings(llm_provider="groq", groq_api_key="test-key"))

    assert isinstance(client, GroqClient)
    assert client.provider == "groq"
    assert client.model == "llama-3.3-70b-versatile"


def test_explicit_model_overrides_the_default() -> None:
    client = build_llm_client(
        _settings(
            llm_provider="gemini",
            gemini_api_key="test-key",
            llm_model="gemini-2.5-pro",
        )
    )

    assert client.model == "gemini-2.5-pro"
