"""Tests for provider selection in build_llm_client.

These never touch the network: constructing a provider client only configures an SDK
object; no request is made until ``complete`` is called.
"""

from __future__ import annotations

import pytest

from aletheia.config import Settings
from aletheia.llm import FallbackLLMClient, LLMConfigurationError, build_llm_client
from aletheia.llm.gemini import GeminiClient
from aletheia.llm.groq import GroqClient
from aletheia.llm.openrouter import OpenRouterClient


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
    assert client.model == "gemini-3.5-flash"


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


def test_no_fallback_returns_a_bare_provider_client() -> None:
    client = build_llm_client(_settings(llm_provider="groq", groq_api_key="test-key"))

    assert not isinstance(client, FallbackLLMClient)


def test_fallback_provider_wraps_primary_in_a_fallback_client() -> None:
    client = build_llm_client(
        _settings(
            llm_provider="groq",
            groq_api_key="groq-key",
            llm_fallback_provider="gemini",
            gemini_api_key="gemini-key",
        )
    )

    assert isinstance(client, FallbackLLMClient)
    # The primary is reported for identification; the fallback uses its own default model.
    assert client.provider == "groq"
    assert client.model == "llama-3.3-70b-versatile"


def test_fallback_duplicating_the_primary_is_rejected() -> None:
    with pytest.raises(LLMConfigurationError, match="duplicates"):
        build_llm_client(
            _settings(
                llm_provider="groq",
                groq_api_key="groq-key",
                llm_fallback_provider="groq",
            )
        )


def test_fallback_without_its_key_fails_loudly() -> None:
    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        build_llm_client(
            _settings(
                llm_provider="groq",
                groq_api_key="groq-key",
                llm_fallback_provider="gemini",  # gemini_api_key stays None
            )
        )


def test_openrouter_with_key_uses_default_model() -> None:
    client = build_llm_client(_settings(llm_provider="openrouter", openrouter_api_key="test-key"))

    assert isinstance(client, OpenRouterClient)
    assert client.provider == "openrouter"
    assert client.model == "nvidia/nemotron-3-ultra-550b-a55b:free"


def test_openrouter_without_key_raises() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENROUTER_API_KEY"):
        build_llm_client(_settings(llm_provider="openrouter"))


def test_three_provider_chain_builds_correctly() -> None:
    client = build_llm_client(
        _settings(
            llm_provider="groq",
            groq_api_key="groq-key",
            llm_fallback_provider="gemini",
            gemini_api_key="gemini-key",
            llm_fallback_provider_2="openrouter",
            openrouter_api_key="or-key",
        )
    )

    assert isinstance(client, FallbackLLMClient)
    assert client.provider == "groq"
