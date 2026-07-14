"""Password hashing, JWT issuance/verification, and BYO-key encryption at rest.

Three independent concerns, kept in one auditable module rather than scattered across
routes:

* Passwords are hashed with argon2 (via passlib) — never stored or compared in plain.
* Sessions are a JWT in an httpOnly cookie (no refresh tokens, no revocation list; a
  pragmatic choice for a research project, documented in the accounts ADR/plan).
* A user's own provider key is encrypted with Fernet under a server-held master key
  (``ENCRYPTION_KEY``) before it is ever written to the database.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from aletheia.accounts.models import Role
from aletheia.config import Settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return str(_pwd_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return bool(_pwd_context.verify(password, password_hash))


def create_access_token(*, user_id: uuid.UUID, role: Role | str, settings: Settings) -> str:
    """Issue a signed JWT carrying the user id and role, expiring per settings.

    Callers are expected to have already checked ``settings.jwt_secret`` is set (every
    route that reaches here does, via ``_require_jwt_secret``/the dependency layer).
    ``role`` accepts a plain ``str`` too: the ORM column is a checked ``String``, not a
    native SQLAlchemy ``Enum``, so a value freshly loaded from the database is a ``str``
    even though the model's Python type is ``Role``.
    """
    if settings.jwt_secret is None:
        raise TokenError("JWT_SECRET is not configured.")
    now = dt.datetime.now(dt.UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": Role(role).value,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=_JWT_ALGORITHM)


class TokenError(Exception):
    """The bearer token is missing, malformed, expired, or forged."""


def decode_access_token(token: str, *, settings: Settings) -> tuple[uuid.UUID, Role]:
    """Verify and decode a JWT, returning the user id and role it carries."""
    if settings.jwt_secret is None:
        raise TokenError("JWT_SECRET is not configured.")
    try:
        payload = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=[_JWT_ALGORITHM]
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc
    try:
        return uuid.UUID(payload["sub"]), Role(payload["role"])
    except (KeyError, ValueError) as exc:
        raise TokenError("token payload is malformed") from exc


class EncryptionNotConfigured(Exception):
    """``ENCRYPTION_KEY`` is unset; BYO-key storage is unavailable."""


def _fernet(settings: Settings) -> Fernet:
    if settings.encryption_key is None:
        raise EncryptionNotConfigured(
            "Storing your own API key requires ENCRYPTION_KEY to be configured on the "
            'server. Generate one with `python -c "from cryptography.fernet import '
            'Fernet; print(Fernet.generate_key().decode())"` and set it in .env.'
        )
    return Fernet(settings.encryption_key.get_secret_value().encode())


def encrypt_key(plaintext: str, *, settings: Settings) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str, *, settings: Settings) -> str:
    try:
        return _fernet(settings).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise EncryptionNotConfigured(
            "Stored key could not be decrypted; ENCRYPTION_KEY may have changed since "
            "it was saved. Re-enter your API key."
        ) from exc
