"""Integration tests for idempotent persistence against a real PostgreSQL + pgvector.

Marked ``integration`` (excluded by default; run with ``-m integration``) because they
need a live database with the ``vector`` extension — the unit suite covers the pure
assembly path. Each test starts from a freshly recreated schema and uses the offline
:class:`FakeEmbedder`, so no model download or network is involved.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aletheia.config import get_settings
from aletheia.corpus.chunking import ChunkConfig
from aletheia.corpus.connectors import FetchedSource, RawDocument
from aletheia.corpus.ingest import ingest
from aletheia.corpus.models import Chunk, Document, Source
from aletheia.db.base import Base
from aletheia.embeddings.fake import FakeEmbedder

pytestmark = [pytest.mark.integration, pytest.mark.database]


def _fetched(abstract: str) -> FetchedSource:
    return FetchedSource(
        connector="pubmed",
        external_id="40000001",
        title="Low-dose aspirin and cardiovascular risk",
        documents=(
            RawDocument(kind="title", text="Low-dose aspirin and cardiovascular risk", ordinal=0),
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


async def test_ingest_persists_the_full_graph_with_embeddings(session: AsyncSession) -> None:
    report = await ingest(session, [_fetched("aspirin reduces fever")], embedder=FakeEmbedder())

    assert [source.status for source in report.sources] == ["created"]
    assert await session.scalar(select(func.count(Source.id))) == 1
    assert await session.scalar(select(func.count(Document.id))) == 2
    chunks = (await session.scalars(select(Chunk))).all()
    assert chunks and all(len(chunk.embedding) == FakeEmbedder().dimension for chunk in chunks)


async def test_ingest_is_idempotent(session: AsyncSession) -> None:
    await ingest(session, [_fetched("aspirin reduces fever")], embedder=FakeEmbedder())
    report = await ingest(session, [_fetched("aspirin reduces fever")], embedder=FakeEmbedder())

    assert [source.status for source in report.sources] == ["skipped"]
    assert await session.scalar(select(func.count(Source.id))) == 1


async def test_replace_rebuilds_the_source(session: AsyncSession) -> None:
    await ingest(session, [_fetched("one sentence.")], embedder=FakeEmbedder())
    long_abstract = " ".join(f"finding{i}" for i in range(400))
    report = await ingest(
        session,
        [_fetched(long_abstract)],
        embedder=FakeEmbedder(),
        chunking=ChunkConfig(max_chars=120, overlap=20),
        replace=True,
    )

    assert [source.status for source in report.sources] == ["replaced"]
    assert await session.scalar(select(func.count(Source.id))) == 1
    # The rebuilt abstract now spans several chunks.
    assert report.sources[0].chunks > 2


async def test_generated_tsvector_supports_keyword_search(session: AsyncSession) -> None:
    await ingest(session, [_fetched("aspirin reduces fever in adults")], embedder=FakeEmbedder())

    matches = await session.scalar(
        select(func.count(Chunk.id)).where(
            Chunk.content_tsv.op("@@")(func.plainto_tsquery("english", "aspirin"))
        )
    )
    assert matches and matches >= 1
