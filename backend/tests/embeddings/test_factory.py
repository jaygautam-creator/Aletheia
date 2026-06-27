"""Tests for provider selection in build_embedder.

These never touch the network or download a model: the local embedder loads its ONNX
model lazily on first use, and constructing the Gemini client only configures an SDK
object. No vectors are produced here.
"""

from __future__ import annotations

import pytest

from aletheia.config import Settings
from aletheia.corpus.models import EMBEDDING_DIM
from aletheia.embeddings import EmbeddingConfigurationError, build_embedder
from aletheia.embeddings.gemini import DEFAULT_GEMINI_EMBED_MODEL, GeminiEmbedder
from aletheia.embeddings.local import DEFAULT_LOCAL_MODEL, LocalEmbedder


def _settings(**overrides: object) -> Settings:
    """Build hermetic settings: ignore any local .env and OS-provided keys."""
    base: dict[str, object] = {"gemini_api_key": None, "groq_api_key": None}
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_default_provider_is_local() -> None:
    embedder = build_embedder(_settings())

    assert isinstance(embedder, LocalEmbedder)
    assert embedder.provider == "local"
    assert embedder.model == DEFAULT_LOCAL_MODEL
    assert embedder.dimension == EMBEDDING_DIM


def test_gemini_without_key_raises() -> None:
    with pytest.raises(EmbeddingConfigurationError, match="GEMINI_API_KEY"):
        build_embedder(_settings(embedding_provider="gemini"))


def test_gemini_with_key_builds_embedder_at_schema_dimension() -> None:
    embedder = build_embedder(_settings(embedding_provider="gemini", gemini_api_key="test-key"))

    assert isinstance(embedder, GeminiEmbedder)
    assert embedder.model == DEFAULT_GEMINI_EMBED_MODEL
    assert embedder.dimension == EMBEDDING_DIM


def test_explicit_model_overrides_the_default() -> None:
    embedder = build_embedder(_settings(embedding_model="BAAI/bge-base-en-v1.5"))
    assert embedder.model == "BAAI/bge-base-en-v1.5"
