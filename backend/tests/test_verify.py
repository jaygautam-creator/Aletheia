"""Tests for the /verify endpoint, with the pipeline backed by a scripted model."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from aletheia.agents import VerificationPipeline
from aletheia.api.routes.verify import get_pipeline
from aletheia.llm import FakeLLMClient, Message
from aletheia.main import app

EVIDENCE = "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911."
ANSWER = "Marie Curie won the 1903 Nobel Prize in Physics. She also discovered penicillin."


def _router(messages: Sequence[Message], json_mode: bool) -> str:
    system = messages[0].content
    user = messages[-1].content
    if "decompose" in system:  # generator decomposing the supplied answer
        return (
            '{"claims": ["Marie Curie won the 1903 Nobel Prize in Physics.", '
            '"Marie Curie discovered penicillin."]}'
        )
    if "penicillin" in user:  # verifier: planted claim with a fabricated quote
        return '{"verdict": "Supported", "quoted_span": "discovered penicillin", "reasoning": "x"}'
    span = "Nobel Prize in Physics in 1903"
    return f'{{"verdict": "Supported", "quoted_span": "{span}", "reasoning": "y"}}'


def _client_with(llm: FakeLLMClient) -> TestClient:
    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(llm)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_verify_returns_a_grounded_result() -> None:
    client = _client_with(FakeLLMClient(_router))

    response = client.post(
        "/verify",
        json={
            "query": "What is Marie Curie known for?",
            "evidence": EVIDENCE,
            "candidate_answer": ANSWER,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_answer"] == ANSWER
    assert body["has_unsupported_claims"] is True
    assert body["support_ratio"] == 0.5

    verdicts = body["verdicts"]
    assert len(verdicts) == 2
    assert verdicts[0]["verdict"] == "Supported"
    assert verdicts[1]["verdict"] == "Unverifiable"
    assert verdicts[1]["quoted_span"] is None


def test_verify_rejects_empty_query() -> None:
    client = _client_with(FakeLLMClient(_router))

    response = client.post("/verify", json={"query": "", "evidence": EVIDENCE})

    assert response.status_code == 422


def test_verify_maps_model_failure_to_502() -> None:
    # An empty script makes the first model call fail, surfacing as a bad-gateway error.
    client = _client_with(FakeLLMClient([]))

    response = client.post(
        "/verify",
        json={"query": "q", "evidence": EVIDENCE, "candidate_answer": ANSWER},
    )

    assert response.status_code == 502
