"""Application configuration loaded from environment variables.

Settings are added as the subsystems that need them land, keeping the surface area
honest at every step. Phase 1 introduces the provider-agnostic LLM configuration;
Phase 2 adds the database connection that backs the corpus and retrieval.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    # "json" emits one structured object per line (with the request id) for the
    # deployed demo's log collector; "plain" stays the human-readable local default.
    log_format: Literal["plain", "json"] = "plain"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL + pgvector connection backing the corpus and hybrid retrieval. The
    # default matches the local docker-compose service; production supplies its own
    # via DATABASE_URL. The async psycopg driver is required (postgresql+psycopg).
    database_url: str = (
        "postgresql+psycopg://aletheia:local-dev-only-change-me@localhost:5432/aletheia"
    )
    db_echo: bool = False

    # LLM provider selection. The system is provider-agnostic; keys are supplied
    # per-environment and never committed. Leave llm_model unset to use the active
    # provider's default model.
    llm_provider: Literal["gemini", "groq", "openrouter"] = "gemini"
    llm_model: str | None = None
    # Optional fail-over chain. When set (and distinct from the primary), the client
    # falls over in order: primary → fallback → fallback_2. Each must differ from the
    # one before it; its key must be present so a misconfigured fallback fails loudly.
    llm_fallback_provider: Literal["gemini", "groq", "openrouter"] | None = None
    llm_fallback_provider_2: Literal["gemini", "groq", "openrouter"] | None = None
    gemini_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None

    # Intake scope guard. When enabled, the API pipeline classifies each query before
    # generating: out-of-domain (non-medical) input and prompt-injection attempts are
    # refused with a clear reason instead of answered. Costs one short LLM call per
    # request; set to false to disable (e.g. to save quota).
    scope_guard_enabled: bool = True

    # Public-demo protection (ADR-0007). A value > 0 arms a per-IP token bucket over
    # the /verify endpoints (the LLM-spending routes); 0 leaves it dormant for local
    # development — but APP_ENV=production refuses to start without it (see
    # main.create_app). ``rate_limit_burst`` is the bucket capacity, i.e. how many
    # requests one address may fire before the per-minute refill governs.
    # ``trust_proxy_headers`` takes the client IP from the last X-Forwarded-For entry;
    # enable it only behind a trusted platform proxy, never on a directly exposed port.
    rate_limit_per_minute: int = 0
    rate_limit_burst: int = 10
    trust_proxy_headers: bool = False
    # Cap on any request body (bytes). A verification request is a query plus
    # optional pasted evidence; 256 KiB is generous headroom, not a constraint.
    max_request_bytes: int = 262_144

    # Accounts (signup/login/profile/history). JWT_SECRET signs session cookies and is
    # required whenever an account route is exercised; APP_ENV=production refuses to
    # start without it (see main.create_app), mirroring the rate-limit guard.
    # ENCRYPTION_KEY (a Fernet key) is required only to store/decrypt a user's own
    # provider key; leaving it unset disables BYO-key storage with a clear 503 rather
    # than crashing. COOKIE_SECURE should stay true except for local http development.
    jwt_secret: SecretStr | None = None
    jwt_expire_minutes: int = 60 * 24 * 7
    encryption_key: SecretStr | None = None
    cookie_secure: bool = True

    # Multimodal claim intake (/extract, ADR-0009). Uploads are processed in memory
    # and never stored; ``max_upload_bytes`` caps the multipart body on /extract only
    # (the strict ``max_request_bytes`` still governs every JSON route). Images are
    # read by ``vision_model`` (reuses GEMINI_API_KEY), voice notes by
    # ``transcription_model`` (reuses GROQ_API_KEY). Extracted text is truncated to
    # ``extract_max_chars`` — the target is a claim to review, not a document dump.
    max_upload_bytes: int = 10_485_760
    # gemini-2.5-flash is the vision default on purpose: it is the stable free-tier
    # multimodal model. The newer gemini-3.5-flash is frequently 503 "high demand"
    # on the free tier, and gemini-2.0-flash carries no free image quota — both
    # break the free-tier-only demo (ANTI_DRIFT non-negotiable). Override per-env.
    vision_model: str = "gemini-2.5-flash"
    transcription_model: str = "whisper-large-v3-turbo"
    extract_max_chars: int = 4_000

    # Embedding provider for the corpus and queries. The default is a local ONNX model
    # (free, offline, reproducible — ADR-0006); "gemini" is a drop-in API alternative
    # that reuses GEMINI_API_KEY. Leave embedding_model unset for the provider default.
    embedding_provider: Literal["local", "gemini"] = "local"
    embedding_model: str | None = None

    # NCBI E-utilities politeness/quota. Both are optional: supplying an email (and
    # optionally a free API key) identifies the client and lifts the request-rate limit.
    # Only the corpus-ingestion CLI uses these; they are never needed to serve requests.
    ncbi_email: str | None = None
    ncbi_api_key: SecretStr | None = None

    # Hybrid retrieval (Phase 2). ``retrieval_candidates`` is the size of the pool pulled
    # from each branch (semantic + keyword) before fusion; ``retrieval_top_k`` is how many
    # fused results are returned as evidence; ``rrf_k`` is the Reciprocal Rank Fusion
    # constant (higher flattens the weighting of top ranks). All have safe defaults.
    retrieval_top_k: int = 8
    retrieval_candidates: int = 20
    rrf_k: int = 60

    # Accepts a comma-separated string (e.g. "http://a,http://b") from the
    # environment; NoDecode disables JSON parsing so the validator below runs.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("llm_fallback_provider", "llm_fallback_provider_2", mode="before")
    @classmethod
    def _blank_fallback_is_disabled(cls, value: object) -> object:
        # A blank `LLM_FALLBACK_PROVIDER=` (the .env.example default) means "no fallback",
        # not an invalid literal — map empty/whitespace to None so startup doesn't fail.
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance for the process lifetime."""
    return Settings()
