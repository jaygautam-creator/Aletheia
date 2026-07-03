"""Tests for the metric surface: stage timing, HTTP metrics, and the /metrics endpoint."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from aletheia.main import app
from aletheia.observability import timed_stages

client = TestClient(app)


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@dataclass(frozen=True)
class _Stage:
    stage: str


async def _stream(*names: str) -> AsyncIterator[_Stage]:
    for name in names:
        yield _Stage(name)


def test_timed_stages_observes_one_duration_per_stage_and_passes_through() -> None:
    generator_before = _sample(
        "aletheia_pipeline_stage_duration_seconds_count", {"stage": "generator"}
    )
    verifier_before = _sample(
        "aletheia_pipeline_stage_duration_seconds_count", {"stage": "verifier"}
    )

    async def _collect() -> list[_Stage]:
        return [stage async for stage in timed_stages(_stream("generator", "verifier"))]

    stages = asyncio.run(_collect())

    assert [s.stage for s in stages] == ["generator", "verifier"]  # untouched pass-through
    assert (
        _sample("aletheia_pipeline_stage_duration_seconds_count", {"stage": "generator"})
        == generator_before + 1
    )
    assert (
        _sample("aletheia_pipeline_stage_duration_seconds_count", {"stage": "verifier"})
        == verifier_before + 1
    )


def test_http_requests_are_counted_by_route_template_and_status() -> None:
    before = _sample(
        "aletheia_http_requests_total", {"method": "GET", "route": "/health", "status": "200"}
    )

    assert client.get("/health").status_code == 200

    after = _sample(
        "aletheia_http_requests_total", {"method": "GET", "route": "/health", "status": "200"}
    )
    assert after == before + 1


def test_unmatched_paths_collapse_into_one_label_value() -> None:
    before = _sample(
        "aletheia_http_requests_total",
        {"method": "GET", "route": "(unmatched)", "status": "404"},
    )

    # A URL scanner must not mint unbounded label values from raw paths.
    assert client.get("/wp-admin/setup.php").status_code == 404
    assert client.get("/another/random/probe").status_code == 404

    after = _sample(
        "aletheia_http_requests_total",
        {"method": "GET", "route": "(unmatched)", "status": "404"},
    )
    assert after == before + 2


def test_metrics_endpoint_exposes_the_registry() -> None:
    client.get("/health")  # guarantee at least one sample exists

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "aletheia_http_requests_total" in response.text
    assert "aletheia_pipeline_stage_duration_seconds" in response.text
