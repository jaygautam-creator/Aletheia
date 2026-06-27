"""Provider-agnostic text embeddings for the corpus and queries.

Agents and ingestion depend only on the abstract :class:`Embedder`; the concrete
provider (local ONNX by default, Gemini as an alternative) is chosen by settings via
:func:`build_embedder`. :class:`FakeEmbedder` gives deterministic, offline vectors for
tests.
"""

from aletheia.embeddings.base import Embedder, EmbeddingConfigurationError, EmbeddingError
from aletheia.embeddings.factory import build_embedder
from aletheia.embeddings.fake import FakeEmbedder

__all__ = [
    "Embedder",
    "EmbeddingConfigurationError",
    "EmbeddingError",
    "FakeEmbedder",
    "build_embedder",
]
