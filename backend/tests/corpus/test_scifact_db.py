"""Integration test: ingesting the SciFact corpus into PostgreSQL + pgvector.

Marked ``integration`` + ``database`` (CI runs these against the pgvector service) because
they exercise the real persistence path. The offline :class:`FakeEmbedder` keeps vectors
deterministic and avoids any model download.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aletheia.config import get_settings
from aletheia.corpus.connectors.scifact import ScifactConnector
from aletheia.corpus.ingest import ingest
from aletheia.corpus.models import Chunk, Source, TrustTier
from aletheia.db.base import Base
from aletheia.embeddings.fake import FakeEmbedder

pytestmark = [pytest.mark.integration, pytest.mark.database]

_CORPUS = (
    '{"doc_id": 4983, "title": "Low-dose aspirin", '
    '"abstract": ["Aspirin reduces cardiovascular risk in older adults."], "structured": false}\n'
    '{"doc_id": 7201, "title": "Vitamin C", '
    '"abstract": ["Vitamin C shows no effect on the common cold."], "structured": false}\n'
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


async def test_ingest_persists_scifact_abstracts_and_indexes_them(session: AsyncSession) -> None:
    sources = ScifactConnector().parse(_CORPUS)

    report = await ingest(session, sources, embedder=FakeEmbedder())

    assert [source.status for source in report.sources] == ["created", "created"]
    assert await session.scalar(select(func.count(Source.id))) == 2
    # The abstract text is keyword-searchable via the generated tsvector.
    matches = await session.scalar(
        select(func.count(Chunk.id)).where(
            Chunk.content_tsv.op("@@")(func.plainto_tsquery("english", "aspirin"))
        )
    )
    assert matches and matches >= 1


async def test_ingested_scifact_sources_are_tagged_curated_corpus(session: AsyncSession) -> None:
    await ingest(session, ScifactConnector().parse(_CORPUS), embedder=FakeEmbedder())

    stored = (await session.scalars(select(Source))).all()
    assert stored and all(source.connector == "scifact" for source in stored)
    assert all(source.trust_tier is TrustTier.CURATED_CORPUS for source in stored)
