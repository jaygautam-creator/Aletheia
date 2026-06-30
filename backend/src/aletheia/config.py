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
    llm_provider: Literal["gemini", "groq"] = "gemini"
    llm_model: str | None = None
    # Optional fail-over provider. When set (and distinct from llm_provider), the client
    # falls over to it — on its own default model — if the primary is exhausted. Its key
    # must be present, so a misconfigured fallback fails loudly rather than silently.
    llm_fallback_provider: Literal["gemini", "groq"] | None = None
    gemini_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

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

    @field_validator("llm_fallback_provider", mode="before")
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
