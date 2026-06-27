"""A deterministic, offline embedder for tests and key-free CI.

Real embedders download a model or call an API, so they have no place in unit tests.
``FakeEmbedder`` derives a stable unit vector from a hash of the input text: identical
text always yields the identical vector, different text yields a different one — enough
to drive nearest-neighbour ordering deterministically without any model or network.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from aletheia.embeddings.base import Embedder

DEFAULT_FAKE_DIMENSION = 384


class FakeEmbedder(Embedder):
    """A scripted :class:`Embedder` producing deterministic unit vectors."""

    provider = "fake"

    def __init__(
        self, *, model: str = "fake-embed-1", dimension: int = DEFAULT_FAKE_DIMENSION
    ) -> None:
        super().__init__(model=model, dimension=dimension)
        self.calls: list[list[str]] = []

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        """A deterministic pseudo-random unit vector seeded by the text."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [0.0] * self.dimension
        for index in range(self.dimension):
            high = digest[(index * 2) % len(digest)]
            low = digest[(index * 2 + 1) % len(digest)]
            raw[index] = ((high << 8 | low) / 65535.0) * 2.0 - 1.0
        norm = math.sqrt(sum(value * value for value in raw)) or 1.0
        return [value / norm for value in raw]

    @property
    def call_count(self) -> int:
        """How many times :meth:`embed_documents` has been called."""
        return len(self.calls)
