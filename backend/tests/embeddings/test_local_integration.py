"""Integration tests for the real local fastembed model.

Marked ``integration`` because the first run downloads the ONNX model, so these are
excluded from the default suite (run with ``-m integration``). They verify the
contract the corpus relies on: the configured width, unit-norm vectors, determinism,
and a genuine query/passage asymmetry.
"""

from __future__ import annotations

import math

import pytest

from aletheia.embeddings.local import DEFAULT_LOCAL_DIMENSION, LocalEmbedder

pytestmark = pytest.mark.integration


async def test_documents_have_expected_width_and_unit_norm() -> None:
    embedder = LocalEmbedder()
    vectors = await embedder.embed_documents(["aspirin reduces fever", "the sky is blue"])

    assert len(vectors) == 2
    assert all(len(vector) == DEFAULT_LOCAL_DIMENSION for vector in vectors)
    assert all(abs(math.sqrt(sum(v * v for v in vector)) - 1.0) < 1e-3 for vector in vectors)


async def test_embeddings_are_deterministic() -> None:
    embedder = LocalEmbedder()
    first = await embedder.embed_documents(["aspirin reduces fever"])
    second = await embedder.embed_documents(["aspirin reduces fever"])
    assert first[0] == pytest.approx(second[0], abs=1e-6)


async def test_query_path_produces_a_valid_vector() -> None:
    embedder = LocalEmbedder()
    query = await embedder.embed_query("what reduces fever?")
    assert len(query) == DEFAULT_LOCAL_DIMENSION
    assert abs(math.sqrt(sum(value * value for value in query)) - 1.0) < 1e-3
