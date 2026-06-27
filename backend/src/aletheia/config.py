"""Application configuration loaded from environment variables.

Settings are added as the subsystems that need them land, keeping the surface area
honest at every step. Phase 1 introduces the provider-agnostic LLM configuration;
database and cache settings arrive with retrieval in Phase 2.
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

    # LLM provider selection. The system is provider-agnostic; keys are supplied
    # per-environment and never committed. Leave llm_model unset to use the active
    # provider's default model.
    llm_provider: Literal["gemini", "groq"] = "gemini"
    llm_model: str | None = None
    gemini_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

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


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance for the process lifetime."""
    return Settings()
