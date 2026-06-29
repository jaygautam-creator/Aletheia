"""Integration tests for hybrid retrieval against a real PostgreSQL + pgvector.

Marked ``integration`` (excluded by default; run with ``-m integration``) because the
two branches use pgvector's cosine operator and the generated ``tsvector`` — the unit
suite covers the pure fusion and assembly. A small corpus is ingested with the offline
:class:`FakeEmbedder`, whose vectors are deterministic, so embedding the exact text of a
chunk reproduces that chunk's stored vector and pins the semantic ranking.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aletheia.config import get_settings
from aletheia.corpus.connectors import FetchedSource, RawDocument
from aletheia.corpus.ingest import ingest
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievalConfig, Retriever
from aletheia.db.base import Base
from aletheia.embeddings.fake import FakeEmbedder

pytestmark = pytest.mark.integration

ASPIRIN_ABSTRACT = "Low-dose aspirin reduces cardiovascular risk in older adults."
VITAMIN_ABSTRACT = "Vitamin C supplementation shows no effect on the common cold."


def _source(external_id: str, title: str, abstract: str) -> FetchedSource:
    return FetchedSource(
        connector="pubmed",
        external_id=external_id,
        title=title,
        documents=(
            RawDocument(kind="title", text=title, ordinal=0),
            RawDocument(kind="abstract", text=abstract, ordinal=1),
        ),
    )


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as opened:
        yield opened
    await engine.dispose()


@pytest.fixture
async def corpus(session: AsyncSession) -> AsyncSession:
    await ingest(
        session,
        [
            _source("1", "Aspirin and cardiovascular risk", ASPIRIN_ABSTRACT),
            _source("2", "Vitamin C and the common cold", VITAMIN_ABSTRACT),
        ],
        embedder=FakeEmbedder(),
    )
    return session


async def test_search_returns_trust_tiered_evidence(corpus: AsyncSession) -> None:
    retriever = Retriever(corpus, embedder=FakeEmbedder())

    results = await retriever.search(ASPIRIN_ABSTRACT)

    assert results, "expected at least one hit"
    # Every result is tiered (ADR-0003) and the best hit is the aspirin abstract, which
    # both branches favour: keyword overlap and an exact embedding match.
    assert all(item.trust_tier is TrustTier.CURATED_CORPUS for item in results)
    assert results[0].text == ASPIRIN_ABSTRACT
    assert results[0].connector == "pubmed"
    assert results[0].external_id == "1"


async def test_results_are_ordered_by_descending_fused_score(corpus: AsyncSession) -> None:
    retriever = Retriever(corpus, embedder=FakeEmbedder())

    results = await retriever.search("aspirin cardiovascular risk")

    scores = [item.score for item in results]
    assert scores == sorted(scores, reverse=True)


async def test_keyword_branch_surfaces_lexical_matches(corpus: AsyncSession) -> None:
    retriever = Retriever(corpus, embedder=FakeEmbedder())

    # A query whose embedding matches nothing stored, but whose words hit one abstract.
    results = await retriever.search("vitamin common cold")

    assert any(item.external_id == "2" for item in results)


async def test_top_k_caps_the_number_of_results(corpus: AsyncSession) -> None:
    retriever = Retriever(corpus, embedder=FakeEmbedder(), config=RetrievalConfig(top_k=1))

    results = await retriever.search(ASPIRIN_ABSTRACT)

    assert len(results) == 1


async def test_blank_query_returns_no_evidence(corpus: AsyncSession) -> None:
    retriever = Retriever(corpus, embedder=FakeEmbedder())

    assert await retriever.search("   ") == []
