"""The corpus schema: sources, their documents, and the embedded chunks.

The hierarchy mirrors how medical literature is actually shaped:

* :class:`Source` — one ingested bibliographic record (a PubMed/PMC entry) and its
  provenance, including the **trust tier** that travels with every piece of evidence.
* :class:`Document` — a normalized unit of text within a source (its abstract, a body
  section), so retrieval can stay section-aware.
* :class:`Chunk` — an embedded span of a document; this is the unit the Retriever
  returns and the Verifier quotes. Each chunk carries both a vector embedding (for
  semantic search) and a generated ``tsvector`` (for keyword search), so a single
  table backs the hybrid retrieval introduced later in Phase 2.

Per ADR-0003 there is *no untiered evidence*: the trust tier is authoritative on the
source and is surfaced with every retrieved chunk.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aletheia.db.base import Base

#: Dimensionality of stored embeddings. Matches the default local embedder
#: (``bge-small-en-v1.5``, 384-dim) introduced in the embeddings workstream. Changing
#: the embedding model changes this number and requires a migration plus a re-ingest.
EMBEDDING_DIM = 384


class TrustTier(StrEnum):
    """How far the system trusts the source of a piece of evidence (ADR-0003).

    ``CURATED_CORPUS`` is the high-trust foundation built from PubMed/PMC open access.
    ``LIVE_FALLBACK`` is reserved for the lower-trust live-search tier added in a later
    phase; it is modelled now so that tier slots in without a schema migration.
    """

    CURATED_CORPUS = "curated_corpus"
    LIVE_FALLBACK = "live_fallback"


class Source(Base):
    """One ingested bibliographic record (a PubMed/PMC entry) and its provenance."""

    __tablename__ = "source"
    __table_args__ = (UniqueConstraint("connector", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connector: Mapped[str] = mapped_column(String(32))
    """The connector that ingested this source (e.g. ``"pubmed"``, ``"pmc"``)."""
    external_id: Mapped[str] = mapped_column(String(64))
    """The source's native identifier (PMID / PMCID)."""
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, default=None)
    license: Mapped[str | None] = mapped_column(String(64), default=None)
    trust_tier: Mapped[TrustTier] = mapped_column(
        # native_enum=False stores a VARCHAR; create_constraint=True adds the CHECK so
        # the database enforces the tier (named ck_source_trust_tier via the convention),
        # matching the migration. values_callable stores the lowercase StrEnum *value*
        # ("curated_corpus") rather than the member name. There is no untiered evidence
        # (ADR-0003).
        Enum(
            TrustTier,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="trust_tier",
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    """Connector-specific provenance (authors, journal, publication date)."""
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Document(Base):
    """A normalized unit of text within a source (e.g. its abstract or a section)."""

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    """The section kind (e.g. ``"title"``, ``"abstract"``, ``"body"``)."""
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    """Order of this document within its source."""
    text: Mapped[str] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="documents")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """An embedded span of a document — the unit retrieved as evidence and quoted."""

    __tablename__ = "chunk"
    __table_args__ = (
        # GIN index over the generated tsvector backs keyword (full-text) search.
        Index("ix_chunk_content_tsv", "content_tsv", postgresql_using="gin"),
        # HNSW index backs approximate nearest-neighbour semantic search (cosine).
        Index(
            "ix_chunk_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    """Order of this chunk within its document."""
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), default=None)
    content_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
