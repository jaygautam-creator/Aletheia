"""The provider-agnostic embedding interface and its errors.

Mirrors the LLM client design: a concrete provider implements one method,
:meth:`Embedder.embed_documents`; everything else (query embedding) is expressed on
top, so adding a provider stays cheap and every provider behaves identically to the
Retriever. The interface is async to match the rest of the stack — a CPU-bound local
model runs in a worker thread so it never blocks the event loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar


class EmbeddingError(RuntimeError):
    """Raised when an embedding provider fails or returns an unusable result."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when the embedder cannot be built from the current settings.

    The most common cause is selecting a provider without supplying its API key.
    """


class Embedder(ABC):
    """Async interface every embedding provider implements.

    A single embedding space backs the corpus: documents and queries must be embedded
    by the *same* model, and the vector width must equal the schema's ``EMBEDDING_DIM``.
    Switching providers therefore means re-embedding the corpus — vectors from different
    models are not comparable.
    """

    #: Stable identifier for the provider family (e.g. ``"local"``, ``"gemini"``).
    provider: ClassVar[str]

    def __init__(self, *, model: str, dimension: int) -> None:
        self._model = model
        self._dimension = dimension

    @property
    def model(self) -> str:
        """The concrete embedding model in use."""
        return self._model

    @property
    def dimension(self) -> int:
        """Width of the vectors this embedder produces."""
        return self._dimension

    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of documents/passages, preserving input order."""

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query.

        Defaults to the document path; providers with an asymmetric query/passage
        objective (bge instructions, Gemini retrieval task types) override this.
        """
        vectors = await self.embed_documents([text])
        return vectors[0]
