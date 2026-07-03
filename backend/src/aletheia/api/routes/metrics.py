"""Prometheus exposition endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response

from aletheia.observability import metrics

router = APIRouter(tags=["system"])


@router.get("/metrics", summary="Prometheus metrics")
def metrics_endpoint() -> Response:
    payload, content_type = metrics.render()
    return Response(payload, media_type=content_type)
