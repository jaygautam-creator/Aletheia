"""Offline test of the Phase 3 benchmark runner.

A scripted :class:`FakeLLMClient` plays both systems (routed by the system prompt) and a
fake retriever supplies canned evidence, so the full run — retrieve, verify, baseline,
score, trace — is exercised without a database, a network call, or a model key.
"""

from __future__ import annotations

from collections.abc import Sequence

from aletheia.agents.contracts import Verdict
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.evaluation.benchmark import BenchmarkItem
from aletheia.evaluation.phase3 import baseline_claim_verdict, run_benchmark
from aletheia.llm import FakeLLMClient, Message

EVIDENCE_TEXT = "Aspirin reduces cardiovascular risk in older adults."


def _source() -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=1,
        source_id=1,
        connector="scifact",
        external_id="4983",
        title="Aspirin and cardiovascular risk",
        url=None,
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text=EVIDENCE_TEXT,
        score=0.5,
    )


async def _retrieve(query: str) -> list[RetrievedEvidence]:
    return [_source()]


def _router(messages: Sequence[Message], json_mode: bool) -> str:
    system = messages[0].content
    if "verification critic" in system:  # the grounded Verifier
        # Quote a span that is verbatim in the evidence, so grounding keeps it Supported.
        return (
            '{"verdict": "Supported", "quoted_span": "Aspirin reduces cardiovascular risk", '
            '"reasoning": "stated in the evidence"}'
        )
    return '{"verdict": "Supported"}'  # the single-LLM baseline


def _items() -> list[BenchmarkItem]:
    return [
        BenchmarkItem(id="1", claim="Aspirin reduces cardiovascular risk.", gold=Verdict.SUPPORTED),
        BenchmarkItem(id="2", claim="Vitamin C cures the common cold.", gold=Verdict.CONTRADICTED),
    ]


async def test_run_benchmark_scores_both_systems_and_emits_traces() -> None:
    report = await run_benchmark(_items(), retrieve=_retrieve, llm=FakeLLMClient(_router))

    assert report.n_items == 2

    # Both systems answer Supported for both claims; gold is [Supported, Contradicted].
    for system in (report.grounded, report.baseline):
        assert system.score.accuracy == 0.5  # one of two matches
        assert system.score.catch_rate == 0.0  # the Contradicted claim was not flagged
        assert system.score.false_agreement_rate == 0.5  # half the affirmations were wrong

    # The grounded run is traced, carrying its retrieved span and the verdict.
    assert len(report.traces) == 2
    assert report.traces[0].verdicts[0].verdict == "Supported"
    assert report.traces[0].evidence[0].external_id == "4983"

    # Measurements were captured for both systems.
    assert report.grounded.latency.n == 2
    assert report.grounded.cost.total_tokens > 0
    assert "SciFact benchmark · 2 claims" in report.render()


async def test_baseline_parses_a_three_way_verdict() -> None:
    client = FakeLLMClient('{"verdict": "Unverifiable"}')

    verdict = await baseline_claim_verdict(client, "a claim", "some evidence")

    assert verdict is Verdict.UNVERIFIABLE
