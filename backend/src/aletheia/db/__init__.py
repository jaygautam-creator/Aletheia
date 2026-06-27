"""Database foundation: the declarative base and async session machinery.

This package owns only *connectivity and mapping infrastructure*. Domain tables live
with their domain — the corpus schema is in :mod:`aletheia.corpus.models` — so the
persistence layer stays a thin, reusable seam rather than a god-module.
"""

from aletheia.db.base import Base
from aletheia.db.session import get_engine, get_session, get_sessionmaker

__all__ = ["Base", "get_engine", "get_session", "get_sessionmaker"]
