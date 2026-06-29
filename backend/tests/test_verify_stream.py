"""Tests for the SSE streaming verification endpoint, backed by a scripted model."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from aletheia.agents import VerificationPipeline
from aletheia.api.routes.verify import get_pipeline
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.llm import FakeLLMClient, Message
from aletheia.main import app

ASPIRIN_CHUNK = "Low-dose aspirin reduces cardiovascular risk in older adults."


def _router(messages: Sequence[Message], json_mode: bool) -> str:
    system = messages[0].content
    if "verification critic" in system:
        return (
            '{"verdict": "Supported", "quoted_span": "aspirin reduces cardiovascular risk", '
            '"reasoning": "Stated in the evidence."}'
        )
    return (
        '{"answer": "Aspirin reduces cardiovascular risk.", '
        '"claims": ["Aspirin reduces cardiovascular risk."]}'
    )


def _source() -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=1,
        source_id=1,
        connector="pubmed",
        external_id="40000001",
        title="Aspirin trial",
        url="https://example.test/40000001",
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text=ASPIRIN_CHUNK,
        score=0.42,
    )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_verify_stream_emits_an_event_per_stage() -> None:
    async def retrieve(query: str) -> list[RetrievedEvidence]:
        return [_source()]

    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(
        FakeLLMClient(_router), retrieve=retrieve
    )
    client = TestClient(app)

    response = client.post("/verify/stream", json={"query": "Does aspirin help the heart?"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    # One event per graph node, in order, then a terminal done event.
    for stage in ("retriever", "generator", "verifier", "aggregator", "guardrail", "done"):
        assert f"event: {stage}" in body
    assert "40000001" in body  # the retrieved source is surfaced as a citation
    assert "Supported" in body  # the verdict rides the verifier event
    assert "medical advice" in body.lower()  # the guardrail event carries the disclaimer


def test_verify_stream_reports_a_model_failure_as_an_error_event() -> None:
    # An empty script makes the first model call fail; the stream reports it, not a crash.
    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(FakeLLMClient([]))
    client = TestClient(app)

    response = client.post("/verify/stream", json={"query": "q", "evidence": ASPIRIN_CHUNK})

    assert response.status_code == 200
    assert "event: error" in response.text
