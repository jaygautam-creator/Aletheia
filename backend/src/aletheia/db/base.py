"""The declarative base every ORM model inherits from.

A single, explicit naming convention is attached to the metadata so that constraints
and indexes get deterministic names. Alembic then generates stable, reviewable
migration code instead of database-assigned names that differ per environment — which
matters for a project whose reproducibility is a first-class requirement.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

#: Deterministic names for indexes, constraints, and keys (Alembic best practice).
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base carrying the shared metadata and naming convention."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
