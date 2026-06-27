"""Local, offline embeddings via fastembed (ONNX runtime).

This is Aletheia's default embedder. A small, CPU-only ONNX model
(``BAAI/bge-small-en-v1.5``, 384-dim) gives reproducible, rate-limit-free embeddings
with no API key — exactly what corpus ingestion and benchmark reproducibility need
(ADR-0006). The model is fetched and held on first use; calls run in a worker thread
because fastembed is synchronous and CPU-bound, so the event loop stays free.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

from aletheia.embeddings.base import Embedder, EmbeddingError

if TYPE_CHECKING:
    from fastembed import TextEmbedding

#: Default local model and its known embedding width.
DEFAULT_LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_LOCAL_DIMENSION = 384


class LocalEmbedder(Embedder):
    """An :class:`Embedder` backed by a local fastembed ONNX model."""

    provider = "local"

    def __init__(
        self,
        *,
        model: str = DEFAULT_LOCAL_MODEL,
        dimension: int = DEFAULT_LOCAL_DIMENSION,
    ) -> None:
        super().__init__(model=model, dimension=dimension)
        self._encoder: TextEmbedding | None = None

    def _ensure_encoder(self) -> TextEmbedding:
        """Load the ONNX model on first use (downloads it once, then caches)."""
        if self._encoder is None:
            # Imported lazily so onnxruntime loads only when the local model is used.
            from fastembed import TextEmbedding  # noqa: PLC0415

            self._encoder = TextEmbedding(model_name=self.model)
        return self._encoder

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed, list(texts), is_query=False)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._embed, [text], is_query=True)
        return vectors[0]

    def _embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        encoder = self._ensure_encoder()
        # Use the model's query objective for queries when it has one (some models
        # prepend a search instruction); passages use the plain encoder. For bge-small
        # in this fastembed build the two paths coincide, which is harmless.
        generator = encoder.query_embed(texts) if is_query else encoder.embed(texts)
        vectors = [[float(value) for value in vector] for vector in generator]
        if any(len(vector) != self.dimension for vector in vectors):
            raise EmbeddingError(
                f"{self.model} produced a vector whose width is not {self.dimension}; "
                "the configured EMBEDDING_DIM and the model must agree."
            )
        return vectors
