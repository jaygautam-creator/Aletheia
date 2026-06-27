"""Tests for the deterministic FakeEmbedder used in offline CI."""

from __future__ import annotations

import math

from aletheia.embeddings import FakeEmbedder


def _is_unit(vector: list[float]) -> bool:
    return abs(math.sqrt(sum(value * value for value in vector)) - 1.0) < 1e-9


async def test_documents_are_deterministic_unit_vectors() -> None:
    embedder = FakeEmbedder()
    first = await embedder.embed_documents(["hello world", "different text"])
    second = await embedder.embed_documents(["hello world", "different text"])

    assert first == second  # deterministic across calls
    assert len(first) == 2
    assert all(len(vector) == embedder.dimension for vector in first)
    assert all(_is_unit(vector) for vector in first)
    assert first[0] != first[1]  # distinct text -> distinct vector


async def test_embed_query_matches_the_document_path() -> None:
    embedder = FakeEmbedder()
    query = await embedder.embed_query("hello world")
    document = await embedder.embed_documents(["hello world"])
    assert query == document[0]


async def test_dimension_is_configurable() -> None:
    embedder = FakeEmbedder(dimension=8)
    assert len(await embedder.embed_query("x")) == 8


async def test_empty_input_returns_no_vectors() -> None:
    embedder = FakeEmbedder()
    assert await embedder.embed_documents([]) == []


async def test_calls_are_recorded() -> None:
    embedder = FakeEmbedder()
    await embedder.embed_documents(["a", "b"])
    await embedder.embed_query("c")
    assert embedder.call_count == 2
    assert embedder.calls[0] == ["a", "b"]
