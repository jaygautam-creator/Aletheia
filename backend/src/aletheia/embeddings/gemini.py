"""Google Gemini embeddings adapter — the drop-in alternative to the local model.

Uses the Gemini embedding API with retrieval task types (an asymmetric query/passage
objective) and requests an output width equal to the configured dimension via
Matryoshka truncation, so the vectors fit the corpus schema. Truncated vectors are
re-normalised to unit length. Choosing this provider means embedding the whole corpus
*and* all queries with it — vectors from different providers are not comparable.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import cast

from google import genai
from google.genai import types

from aletheia.embeddings.base import Embedder, EmbeddingError

#: Default Gemini embedding model (supports Matryoshka output dimensions).
DEFAULT_GEMINI_EMBED_MODEL = "gemini-embedding-001"


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class GeminiEmbedder(Embedder):
    """An :class:`Embedder` backed by the Google Gemini embedding API."""

    provider = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_EMBED_MODEL,
        dimension: int,
    ) -> None:
        super().__init__(model=model, dimension=dimension)
        self._client = genai.Client(api_key=api_key)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed(list(texts), task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]

    async def _embed(self, texts: list[str], *, task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.dimension,
        )
        try:
            response = await self._client.aio.models.embed_content(
                model=self.model, contents=cast(types.ContentListUnion, texts), config=config
            )
        except Exception as exc:  # normalise any provider failure
            raise EmbeddingError(f"Gemini embedding request failed: {exc}") from exc

        embeddings = response.embeddings
        if embeddings is None or len(embeddings) != len(texts):
            raise EmbeddingError("Gemini returned an unexpected number of embeddings.")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.values
            if values is None:
                raise EmbeddingError("Gemini returned an embedding with no values.")
            vectors.append(_unit([float(value) for value in values]))
        return vectors
