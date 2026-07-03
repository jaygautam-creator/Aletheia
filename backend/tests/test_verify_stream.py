"""Tests for the SSE streaming verification endpoint, backed by a scripted model."""

from __future__ import annotations

import json
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


def test_verify_stream_skips_the_retriever_when_evidence_is_supplied() -> None:
    # Regression: with a retriever in the graph but evidence supplied by the caller, the
    # Retriever node writes no state. LangGraph surfaces that as a None update; the stream
    # must skip it rather than crash trying to serialize it.
    async def retrieve(query: str) -> list[RetrievedEvidence]:
        return [_source()]

    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(
        FakeLLMClient(_router), retrieve=retrieve
    )
    client = TestClient(app)

    response = client.post(
        "/verify/stream",
        json={"query": "Does aspirin help the heart?", "evidence": ASPIRIN_CHUNK},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: error" not in body
    # The pass-through Retriever produced no update, so it emits no event …
    assert "event: retriever" not in body
    # … while the stages that did run still stream through to the terminal done event.
    for stage in ("generator", "verifier", "aggregator", "guardrail", "done"):
        assert f"event: {stage}" in body


def test_verify_stream_reports_a_retrieval_failure_as_an_error_event() -> None:
    # A non-LLM failure mid-stream (here the corpus search blowing up) must still surface
    # as a terminal error event, not tear the connection down as a bare network error.
    async def retrieve(query: str) -> list[RetrievedEvidence]:
        raise RuntimeError("corpus database unreachable")

    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(
        FakeLLMClient(_router), retrieve=retrieve
    )
    client = TestClient(app)

    response = client.post("/verify/stream", json={"query": "Does aspirin help the heart?"})

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "Verification failed" in response.text


def test_verify_stream_reports_a_model_failure_as_an_error_event() -> None:
    # An empty script makes the first model call fail; the stream reports it, not a crash.
    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(FakeLLMClient([]))
    client = TestClient(app)

    response = client.post("/verify/stream", json={"query": "q", "evidence": ASPIRIN_CHUNK})

    assert response.status_code == 200
    assert "event: error" in response.text


def test_verify_stream_links_each_span_to_its_source_block() -> None:
    async def retrieve(query: str) -> list[RetrievedEvidence]:
        return [_source()]

    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(
        FakeLLMClient(_router), retrieve=retrieve
    )
    client = TestClient(app)

    response = client.post("/verify/stream", json={"query": "Does aspirin help the heart?"})

    assert response.status_code == 200
    # The verifier and aggregator events serialize after the retriever's sources have
    # streamed past, so both carry the resolved link from quoted span to citation [1].
    events = _events_by_name(response.text)
    assert events["verifier"]["verdicts"][0]["source_index"] == 1
    assert events["aggregator"]["result"]["verdicts"][0]["source_index"] == 1


def _events_by_name(body: str) -> dict[str, dict]:
    """Parse an SSE body into {event name: parsed data} (last event of each name wins)."""
    events: dict[str, dict] = {}
    for frame in body.strip().split("\n\n"):
        lines = frame.split("\n")
        name = lines[0].removeprefix("event: ")
        data = "\n".join(line.removeprefix("data: ") for line in lines[1:])
        events[name] = json.loads(data)
    return events
