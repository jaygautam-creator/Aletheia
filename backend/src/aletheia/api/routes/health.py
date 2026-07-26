"""System endpoints: liveness/health."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from aletheia import __version__

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Health-check payload."""

    status: str
    service: str
    version: str


# GET *and* HEAD: uptime monitors (e.g. UptimeRobot) default to HEAD, and a GET-only
# route answers HEAD with 405 — which those monitors read as "down" even while the
# service is healthy. Starlette strips the body from a HEAD response automatically.
@router.api_route(
    "/health",
    methods=["GET", "HEAD"],
    response_model=HealthResponse,
    summary="Liveness/health check",
)
async def health() -> HealthResponse:
    """Report that the service is up and which version is running."""
    return HealthResponse(status="ok", service="aletheia-backend", version=__version__)
