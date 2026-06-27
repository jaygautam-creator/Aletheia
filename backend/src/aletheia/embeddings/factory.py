"""Build the active :class:`Embedder` from application settings.

The single place that knows about concrete embedding providers, mirroring the LLM
factory. The default is the local ONNX model — free, offline, and reproducible
(ADR-0006); Gemini is a drop-in alternative for those who prefer an API and have a key.
The vector width is pinned to the schema's ``EMBEDDING_DIM`` so embeddings always fit
the corpus column.
"""

from __future__ import annotations

from typing import assert_never

from aletheia.config import Settings, get_settings
from aletheia.corpus.models import EMBEDDING_DIM
from aletheia.embeddings.base import Embedder, EmbeddingConfigurationError
from aletheia.embeddings.gemini import DEFAULT_GEMINI_EMBED_MODEL, GeminiEmbedder
from aletheia.embeddings.local import DEFAULT_LOCAL_MODEL, LocalEmbedder


def build_embedder(settings: Settings | None = None) -> Embedder:
    """Return the embedder selected by ``settings`` (defaults to the process settings).

    Raises :class:`EmbeddingConfigurationError` when the chosen provider has no API key.
    """
    settings = settings or get_settings()
    provider = settings.embedding_provider

    if provider == "local":
        return LocalEmbedder(
            model=settings.embedding_model or DEFAULT_LOCAL_MODEL,
            dimension=EMBEDDING_DIM,
        )

    if provider == "gemini":
        if settings.gemini_api_key is None:
            raise EmbeddingConfigurationError(
                "EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                "Add a free key from https://aistudio.google.com/apikey to your .env."
            )
        return GeminiEmbedder(
            api_key=settings.gemini_api_key.get_secret_value(),
            model=settings.embedding_model or DEFAULT_GEMINI_EMBED_MODEL,
            dimension=EMBEDDING_DIM,
        )

    assert_never(provider)
