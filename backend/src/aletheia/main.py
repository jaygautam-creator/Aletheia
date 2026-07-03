"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aletheia import __version__
from aletheia.agents import DISCLAIMER
from aletheia.api.bodylimit import BodySizeLimitMiddleware
from aletheia.api.ratelimit import RateLimitMiddleware
from aletheia.api.routes import health, metrics, verify
from aletheia.config import Settings, get_settings
from aletheia.observability import MetricsMiddleware, RequestIDMiddleware, configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings if settings is not None else get_settings()

    if settings.app_env == "production" and settings.rate_limit_per_minute <= 0:
        raise RuntimeError(
            "APP_ENV=production requires RATE_LIMIT_PER_MINUTE > 0: the public /verify "
            "endpoints spend the shared LLM budget and must be rate limited (ADR-0007)."
        )

    configure_logging(level=settings.log_level, log_format=settings.log_format)

    app = FastAPI(
        title="Aletheia",
        description="Evidence-grounded, multi-agent verification framework.",
        version=__version__,
    )

    # add_middleware nests LIFO — the last one added is outermost. Outer to inner:
    # CORS (so even a 429 carries the CORS headers a browser needs to read it) →
    # request id (so every log line below it is tagged) → metrics (counts throttled
    # requests too) → body cap (an oversized request is refused before it can spend
    # a rate token) → rate limit → routes.
    if settings.rate_limit_per_minute > 0:
        app.add_middleware(
            RateLimitMiddleware,
            per_minute=settings.rate_limit_per_minute,
            burst=settings.rate_limit_burst,
            trust_proxy_headers=settings.trust_proxy_headers,
        )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(verify.router)
    app.include_router(metrics.router)

    @app.get("/", tags=["system"], summary="Service metadata")
    async def root() -> dict[str, str]:
        return {
            "service": "aletheia-backend",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
            "disclaimer": DISCLAIMER,
        }

    return app


app = create_app()
