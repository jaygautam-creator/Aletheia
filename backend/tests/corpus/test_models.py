"""Structural tests for the corpus schema — no database connection required.

These assert the *shape* of the mapped models (tables, columns, the embedding
dimension, the trust-tier invariant, and the source -> document -> chunk
relationships), so the schema contract is locked in offline, key-free CI. Behaviour
against a live PostgreSQL is exercised by the integration tests in later workstreams.
"""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from aletheia.corpus.models import EMBEDDING_DIM, Chunk, Document, Source, TrustTier
from aletheia.db.base import Base


def test_trust_tier_values() -> None:
    assert TrustTier.CURATED_CORPUS.value == "curated_corpus"
    assert TrustTier.LIVE_FALLBACK.value == "live_fallback"


def test_expected_tables_registered() -> None:
    assert set(Base.metadata.tables) == {"source", "document", "chunk"}


def test_chunk_carries_embedding_and_tsvector() -> None:
    columns = set(Chunk.__table__.c.keys())
    assert {"id", "document_id", "ordinal", "text", "embedding", "content_tsv"} <= columns
    assert Chunk.__table__.c.embedding.type.dim == EMBEDDING_DIM


def test_source_is_unique_per_connector_and_external_id() -> None:
    uniques = {
        tuple(col.name for col in constraint.columns)
        for constraint in Source.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("connector", "external_id") in uniques


def test_relationships_link_source_document_chunk() -> None:
    assert Source.documents.property.mapper.class_ is Document
    assert Document.chunks.property.mapper.class_ is Chunk
    assert Chunk.document.property.mapper.class_ is Document


def test_trust_tier_check_constraint_matches_migration() -> None:
    """The trust-tier CHECK must use the convention name and the lowercase values.

    This guards a subtle SQLAlchemy alignment with the 0001 migration: the constraint
    is named via the metadata convention (no doubled prefix), and ``values_callable``
    stores the StrEnum *value* — so the model's emitted DDL matches the migration's.
    """
    ddl = str(CreateTable(Source.__table__).compile(dialect=postgresql.dialect()))
    assert "CONSTRAINT ck_source_trust_tier CHECK" in ddl
    assert "ck_source_ck_source" not in ddl
    assert "trust_tier IN ('curated_corpus', 'live_fallback')" in ddl
