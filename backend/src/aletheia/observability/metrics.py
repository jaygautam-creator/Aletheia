"""The metric surface: three instruments on the default prometheus-client registry.

Hand-rolled rather than an instrumentator dependency because the whole surface is
three instruments (master plan D2): request counts, request durations, and per-stage
pipeline durations. One process, one uvicorn worker — the default registry is exact;
no multiprocess mode needed.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Protocol

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "aletheia_http_requests_total",
    "HTTP requests handled, by method, resolved route template, and status code.",
    ("method", "route", "status"),
)

HTTP_REQUEST_SECONDS = Histogram(
    "aletheia_http_request_duration_seconds",
    "Wall time per HTTP request (for SSE: until the stream closes).",
    ("method", "route"),
)

# Buckets sized for LLM-bound stages: the fast nodes (aggregator, guardrail) land in
# the sub-100ms buckets, model-calling nodes in the seconds range, and the top bucket
# comfortably holds a free-tier rate-limit backoff.
PIPELINE_STAGE_SECONDS = Histogram(
    "aletheia_pipeline_stage_duration_seconds",
    "Wall time per pipeline stage (retriever, generator, verifier, aggregator, guardrail).",
    ("stage",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 40.0),
)


def render() -> tuple[bytes, str]:
    """The registry in Prometheus exposition format, with its content type."""
    return generate_latest(), CONTENT_TYPE_LATEST


class _HasStage(Protocol):
    @property
    def stage(self) -> str: ...


async def timed_stages[StageT: _HasStage](
    stages: AsyncIterator[StageT],
) -> AsyncIterator[StageT]:
    """Pass a stage stream through, recording each stage's duration server-side.

    Graph nodes run sequentially, so the gap between consecutive updates *is* the
    arriving stage's own wall time. The stream path already surfaces these timings
    to the browser; this records the same numbers where Prometheus can see them.
    """
    start = time.perf_counter()
    async for stage in stages:
        now = time.perf_counter()
        PIPELINE_STAGE_SECONDS.labels(stage=stage.stage).observe(now - start)
        start = now
        yield stage
