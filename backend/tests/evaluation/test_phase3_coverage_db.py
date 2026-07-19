"""Integration test for :func:`aletheia.evaluation.phase3.corpus_coverage`.

Regression test for a bug found while setting up the FEVER live run (ADR-0011): the
runner called ``corpus_coverage`` without its ``connector`` argument, so it silently
defaulted to ``"scifact"`` even when scoring a FEVER sample — every claim whose cited
Wikipedia pages were only ingested under the ``fever`` connector was reported as
uncovered, even though the corpus had them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aletheia.agents.contracts import Verdict
from aletheia.config import get_settings
from aletheia.corpus.connectors import FetchedSource, RawDocument
from aletheia.corpus.ingest import ingest
from aletheia.db.base import Base
from aletheia.embeddings.fake import FakeEmbedder
from aletheia.evaluation.benchmark import BenchmarkItem
from aletheia.evaluation.phase3 import corpus_coverage

pytestmark = [pytest.mark.integration, pytest.mark.database]


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
async def fever_corpus(session: AsyncSession) -> AsyncSession:
    await ingest(
        session,
        [
            FetchedSource(
                connector="fever",
                external_id="Aspirin",
                title="Aspirin",
                documents=(RawDocument(kind="body", text="Aspirin is a drug.", ordinal=0),),
            )
        ],
        embedder=FakeEmbedder(),
    )
    return session


async def test_coverage_defaults_to_scifact_and_misses_other_connectors(
    fever_corpus: AsyncSession,
) -> None:
    item = BenchmarkItem(
        id="1", claim="x", gold=Verdict.SUPPORTED, cited_doc_ids=["Aspirin"], dataset="fever"
    )

    coverage = await corpus_coverage(fever_corpus, [item])

    assert coverage.n_covered == 0


async def test_coverage_scoped_to_fever_finds_its_own_sources(fever_corpus: AsyncSession) -> None:
    item = BenchmarkItem(
        id="1", claim="x", gold=Verdict.SUPPORTED, cited_doc_ids=["Aspirin"], dataset="fever"
    )

    coverage = await corpus_coverage(fever_corpus, [item], connector="fever")

    assert coverage.n_covered == 1
