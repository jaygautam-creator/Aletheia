"""Tests for run-trace assembly and JSONL round-tripping."""

from __future__ import annotations

from pathlib import Path

from aletheia.agents.contracts import ClaimVerdict, Verdict, VerificationResult
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.evaluation.trace import RunTrace, build_run_trace, read_traces, write_traces
from aletheia.llm.recording import CallRecord


def _evidence() -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=1,
        source_id=1,
        connector="scifact",
        external_id="4983",
        title="Low-dose aspirin",
        url="https://example.test/4983",
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text="Aspirin reduces cardiovascular risk in older adults.",
        score=0.42,
    )


def _result() -> VerificationResult:
    return VerificationResult(
        query="Does aspirin help the heart?",
        candidate_answer="Aspirin reduces cardiovascular risk.",
        verdicts=[
            ClaimVerdict(
                claim="Aspirin reduces cardiovascular risk.",
                verdict=Verdict.SUPPORTED,
                quoted_span="aspirin reduces cardiovascular risk",
                reasoning="Stated in the evidence.",
            )
        ],
    )


def _trace() -> RunTrace:
    return build_run_trace(
        _result(),
        [_evidence()],
        [CallRecord(model="fake-1", prompt_tokens=10, completion_tokens=4, latency_s=0.01)],
        latency_s=0.5,
    )


def test_build_run_trace_captures_inputs_spans_and_verdicts() -> None:
    trace = _trace()

    assert trace.query == "Does aspirin help the heart?"
    assert trace.latency_s == 0.5
    assert trace.evidence[0].external_id == "4983"
    assert trace.evidence[0].trust_tier == "curated_corpus"  # StrEnum rendered as its value
    assert trace.verdicts[0].verdict == "Supported"
    assert trace.verdicts[0].quoted_span == "aspirin reduces cardiovascular risk"
    # Token usage is summed across the run's calls.
    assert trace.total_usage.total_tokens == 14


def test_traces_round_trip_through_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "traces.jsonl"
    original = [_trace(), _trace()]

    write_traces(path, original)
    restored = read_traces(path)

    assert len(restored) == 2
    assert restored[0] == original[0]  # frozen dataclasses compare by value
    assert restored[1].llm_calls[0].latency_s == 0.01


def test_writing_no_traces_yields_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"

    write_traces(path, [])

    assert path.read_text(encoding="utf-8") == ""
    assert read_traces(path) == []
