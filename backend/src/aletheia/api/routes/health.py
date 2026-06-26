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


@router.get("/health", response_model=HealthResponse, summary="Liveness/health check")
async def health() -> HealthResponse:
    """Report that the service is up and which version is running."""
    return HealthResponse(status="ok", service="aletheia-backend", version=__version__)
