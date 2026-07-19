"""Widen source.external_id to fit FEVER's Wikipedia page ids (ADR-0011)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "source",
        "external_id",
        existing_type=sa.String(length=64),
        type_=sa.String(length=256),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "source",
        "external_id",
        existing_type=sa.String(length=256),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
