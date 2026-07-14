"""accounts schema: users, their encrypted API keys, and the request history/audit log

Creates the three account tables (user, api_key, request_log). ``api_key`` stores each
user's own provider key encrypted (Fernet ciphertext, never plaintext) and is unique
per (user, provider). ``request_log`` records who ran what, when, and whether their own
key or the server default served it — the basis for both "my history" and the admin
audit view.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )
    op.create_index("ix_user_email", "user", ["email"])

    op.create_table(
        "api_key",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_api_key_user_id_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_key"),
        sa.UniqueConstraint("user_id", "provider", name="uq_api_key_user_id"),
    )
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"])

    op.create_table(
        "request_log",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("route", sa.String(length=64), nullable=False),
        sa.Column("query_preview", sa.String(length=200), nullable=True),
        sa.Column("key_source", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_request_log_user_id_user", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_request_log"),
    )
    op.create_index("ix_request_log_user_id", "request_log", ["user_id"])
    op.create_index("ix_request_log_created_at", "request_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_request_log_created_at", table_name="request_log")
    op.drop_index("ix_request_log_user_id", table_name="request_log")
    op.drop_table("request_log")
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_table("api_key")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
