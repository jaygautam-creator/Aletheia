"""Offline tests for the ingestion *assembly* — chunking + embedding into the ORM graph.

The persistence + idempotency path needs a real PostgreSQL (pgvector / tsvector) and is
covered by the integration tests; here we exercise :func:`assemble_source`, which builds
the in-memory ``Source -> Document -> Chunk`` graph without any database.
"""

from __future__ import annotations

from aletheia.corpus.chunking import ChunkConfig, chunk_text
from aletheia.corpus.connectors import FetchedSource, RawDocument
from aletheia.corpus.ingest import assemble_source
from aletheia.corpus.models import EMBEDDING_DIM, TrustTier
from aletheia.embeddings.fake import FakeEmbedder


def _fetched(text: str) -> FetchedSource:
    return FetchedSource(
        connector="pubmed",
        external_id="40000001",
        title="A synthetic title",
        documents=(
            RawDocument(kind="title", text="A synthetic title", ordinal=0),
            RawDocument(kind="abstract", text=text, ordinal=1),
        ),
        url="https://example.test/40000001",
        meta={"journal": "Synthetic"},
    )


async def test_assemble_tags_curated_corpus_and_copies_provenance() -> None:
    source = await assemble_source(_fetched("aspirin reduces fever"), embedder=FakeEmbedder())

    assert source.trust_tier is TrustTier.CURATED_CORPUS
    assert source.connector == "pubmed"
    assert source.external_id == "40000001"
    assert source.url == "https://example.test/40000001"
    assert source.meta == {"journal": "Synthetic"}


async def test_assemble_chunks_each_document_and_embeds_every_chunk() -> None:
    long_text = " ".join(f"finding{i}" for i in range(400))
    embedder = FakeEmbedder()

    source = await assemble_source(
        _fetched(long_text), embedder=embedder, chunking=ChunkConfig(max_chars=120, overlap=20)
    )

    documents = source.documents
    assert [document.kind for document in documents] == ["title", "abstract"]
    # Document ordinals are assigned in order.
    assert [document.ordinal for document in documents] == [0, 1]

    abstract_chunks = documents[1].chunks
    assert len(abstract_chunks) == len(chunk_text(long_text, max_chars=120, overlap=20))
    assert len(abstract_chunks) > 1
    assert [chunk.ordinal for chunk in abstract_chunks] == list(range(len(abstract_chunks)))
    assert all(len(chunk.embedding) == EMBEDDING_DIM for chunk in abstract_chunks)


async def test_assemble_embeds_all_chunks_in_one_batch() -> None:
    embedder = FakeEmbedder()
    await assemble_source(_fetched("aspirin reduces fever"), embedder=embedder)

    # One call covers every chunk across all documents, to amortize model/API overhead.
    assert embedder.call_count == 1


async def test_assemble_handles_documents_with_no_text() -> None:
    fetched = FetchedSource(
        connector="pubmed",
        external_id="x",
        title="t",
        documents=(RawDocument(kind="abstract", text="   ", ordinal=0),),
    )
    source = await assemble_source(fetched, embedder=FakeEmbedder())

    assert len(source.documents) == 1
    assert source.documents[0].chunks == []
