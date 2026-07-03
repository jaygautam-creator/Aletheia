"""Tests for the /verify endpoint, with the pipeline backed by a scripted model."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from aletheia.agents import EvidenceRetriever, VerificationPipeline
from aletheia.api.routes.verify import _source_index_for, get_pipeline
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
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


def _client_with(llm: FakeLLMClient, retrieve: EvidenceRetriever | None = None) -> TestClient:
    app.dependency_overrides[get_pipeline] = lambda: VerificationPipeline(llm, retrieve=retrieve)
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

    # The guardrail advisory rides along: one Unverifiable claim warrants caution, and
    # the disclaimer is always present. The verdict contract above is untouched.
    assert body["safety"]["advisory"] == "caution"
    assert "medical advice" in body["safety"]["disclaimer"].lower()


def test_verify_rejects_empty_query() -> None:
    client = _client_with(FakeLLMClient(_router))

    response = client.post("/verify", json={"query": "", "evidence": EVIDENCE})

    assert response.status_code == 422


ASPIRIN_CHUNK = "Low-dose aspirin reduces cardiovascular risk in older adults."


def _retrieval_router(messages: Sequence[Message], json_mode: bool) -> str:
    system = messages[0].content
    if "verification critic" in system:
        return (
            '{"verdict": "Supported", "quoted_span": "aspirin reduces cardiovascular risk", '
            '"reasoning": "Stated in the evidence."}'
        )
    # Generate-and-decompose path (no candidate answer supplied).
    return (
        '{"answer": "Aspirin reduces cardiovascular risk.", '
        '"claims": ["Aspirin reduces cardiovascular risk."]}'
    )


def test_verify_retrieves_evidence_and_returns_citations_when_evidence_omitted() -> None:
    source = RetrievedEvidence(
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

    async def retrieve(query: str) -> list[RetrievedEvidence]:
        return [source]

    client = _client_with(FakeLLMClient(_retrieval_router), retrieve=retrieve)

    response = client.post("/verify", json={"query": "Does aspirin help the heart?"})

    assert response.status_code == 200
    body = response.json()
    # The verdict contract is intact at the top level...
    assert body["candidate_answer"] == "Aspirin reduces cardiovascular risk."
    assert body["verdicts"][0]["verdict"] == "Supported"
    # ...and the retrieved source is surfaced additively as a trust-tiered citation.
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["index"] == 1
    assert citation["external_id"] == "40000001"
    assert citation["trust_tier"] == "curated_corpus"
    assert citation["url"] == "https://example.test/40000001"
    # The verdict's quoted span is resolved to the citation whose block contains it.
    assert body["verdicts"][0]["source_index"] == 1


def test_verify_with_supplied_evidence_has_no_citations() -> None:
    client = _client_with(FakeLLMClient(_router))

    response = client.post(
        "/verify",
        json={"query": "q", "evidence": EVIDENCE, "candidate_answer": ANSWER},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    # Caller-supplied evidence has no numbered blocks, so there is nothing to link to.
    assert all(verdict["source_index"] is None for verdict in body["verdicts"])


def test_verify_maps_model_failure_to_502() -> None:
    # An empty script makes the first model call fail, surfacing as a bad-gateway error.
    client = _client_with(FakeLLMClient([]))

    response = client.post(
        "/verify",
        json={"query": "q", "evidence": EVIDENCE, "candidate_answer": ANSWER},
    )

    assert response.status_code == 502


def _evidence(index: int, title: str, text: str) -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=index,
        source_id=index,
        connector="pubmed",
        external_id=str(40000000 + index),
        title=title,
        url=None,
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text=text,
        score=0.5,
    )


SOURCES = [
    _evidence(1, "Aspirin trial", "Low-dose aspirin reduces cardiovascular risk."),
    _evidence(2, "Zinc review", "Zinc does not shorten the common cold."),
]


def test_source_index_resolves_a_span_to_its_block() -> None:
    assert _source_index_for("Zinc does not shorten", SOURCES) == 2


def test_source_index_tolerates_whitespace_like_the_grounding_check() -> None:
    # The same normalisation as the grounding check: a re-wrapped quote still resolves.
    assert _source_index_for("Zinc  does\nnot   shorten", SOURCES) == 2


def test_source_index_resolves_a_span_straddling_the_header_line() -> None:
    # The block includes its provenance header, so a quote spilling across the title
    # line and into the text still lands on the right source.
    assert _source_index_for("Aspirin trial\nLow-dose aspirin", SOURCES) == 1


def test_source_index_picks_the_first_of_duplicate_blocks() -> None:
    duplicated = [SOURCES[0], _evidence(2, "Aspirin trial copy", SOURCES[0].text)]

    assert _source_index_for("reduces cardiovascular risk", duplicated) == 1


def test_source_index_omits_an_unresolvable_span() -> None:
    # A span found in no single block — here one straddling two blocks — is omitted,
    # never guessed.
    straddling = "reduces cardiovascular risk. [2] Zinc review"

    assert _source_index_for(straddling, SOURCES) is None
    assert _source_index_for("text from nowhere", SOURCES) is None


def test_source_index_is_none_without_a_span_or_sources() -> None:
    assert _source_index_for(None, SOURCES) is None
    assert _source_index_for("", SOURCES) is None
    assert _source_index_for("Low-dose aspirin", []) is None
