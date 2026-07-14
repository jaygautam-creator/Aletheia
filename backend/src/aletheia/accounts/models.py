"""Accounts schema: users, their stored API keys, and the request history/audit log.

Three tables:

* :class:`User` — an account (email + hashed password) with a coarse ``role``
  (``user``/``admin``, no further RBAC).
* :class:`ApiKey` — one BYO provider key per user per provider, stored encrypted
  (:mod:`aletheia.accounts.security`); the plaintext key is never persisted.
* :class:`RequestLog` — one row per verification/extraction request, recording who
  called what, when, and whether their own key or the server default was used. This is
  both "my history" (per-user query) and the admin audit view (aggregate query).
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aletheia.db.base import Base


class Role(StrEnum):
    """A user's coarse authorization level. No further RBAC is modelled."""

    USER = "user"
    ADMIN = "admin"


class Provider(StrEnum):
    """The LLM providers a user may store a BYO key for. Mirrors ``llm.factory.Provider``."""

    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"


class KeySource(StrEnum):
    """Which key served a logged request."""

    SERVER_DEFAULT = "server_default"
    USER_KEY = "user_key"


class User(Base):
    """An account: email + hashed password, a display name, and a role."""

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120), default=None)
    role: Mapped[Role] = mapped_column(String(16), default=Role.USER)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    """A user's own provider key, encrypted at rest. One row per (user, provider)."""

    __tablename__ = "api_key"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[Provider] = mapped_column(String(16))
    encrypted_key: Mapped[str] = mapped_column(Text)
    """Fernet ciphertext (see :mod:`aletheia.accounts.security`); never plaintext."""
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped[User] = relationship(back_populates="api_keys")


class RequestLog(Base):
    """One row per verification/extraction request: who ran what, when, with which key.

    ``user_id`` is nullable because the verification routes remain usable without an
    account (only BYO-key and history require login); an anonymous request is still
    logged for the admin audit view, just with no attributable user.
    """

    __tablename__ = "request_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), index=True, default=None
    )
    route: Mapped[str] = mapped_column(String(64))
    query_preview: Mapped[str | None] = mapped_column(String(200), default=None)
    """First 200 characters of the query, for the history view. Not the full payload."""
    key_source: Mapped[KeySource] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    """``"ok"``, ``"error"``, or ``"refused"`` (the intake scope guard declined it)."""
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
