"""corpus schema: sources, documents, embedded chunks

Creates the pgvector extension and the three-table corpus hierarchy (source ->
document -> chunk). Each chunk carries a vector embedding (HNSW index, cosine) and a
generated tsvector (GIN index), so one schema backs hybrid semantic + keyword search.
The trust tier is stored on the source as a checked string — there is no untiered
evidence (ADR-0003).

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Embedding dimensionality (bge-small-en-v1.5); see aletheia.corpus.models.EMBEDDING_DIM.
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=64), nullable=True),
        sa.Column("trust_tier", sa.String(length=32), nullable=False),
        sa.Column("meta", JSONB(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "trust_tier IN ('curated_corpus', 'live_fallback')",
            # The metadata naming convention prefixes this token, yielding
            # ck_source_trust_tier — matching what the Enum on the model emits.
            name="trust_tier",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source"),
        sa.UniqueConstraint("connector", "external_id", name="uq_source_connector"),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source.id"],
            name="fk_document_source_id_source",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document"),
    )
    op.create_index("ix_document_source_id", "document", ["source_id"])

    op.create_table(
        "chunk",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "content_tsv",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["document.id"],
            name="fk_chunk_document_id_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunk"),
    )
    op.create_index("ix_chunk_document_id", "chunk", ["document_id"])
    op.create_index("ix_chunk_content_tsv", "chunk", ["content_tsv"], postgresql_using="gin")
    op.create_index(
        "ix_chunk_embedding_hnsw",
        "chunk",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_embedding_hnsw", table_name="chunk")
    op.drop_index("ix_chunk_content_tsv", table_name="chunk")
    op.drop_index("ix_chunk_document_id", table_name="chunk")
    op.drop_table("chunk")
    op.drop_index("ix_document_source_id", table_name="document")
    op.drop_table("document")
    op.drop_table("source")
    op.execute("DROP EXTENSION IF EXISTS vector")
