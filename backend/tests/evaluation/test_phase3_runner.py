"""Offline test of the Phase 3 benchmark runner.

A scripted :class:`FakeLLMClient` plays both systems (routed by the system prompt) and a
fake retriever supplies canned evidence, so the full run — retrieve, verify, baseline,
score, trace — is exercised without a database, a network call, or a model key.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.evaluation.benchmark import BenchmarkItem
from aletheia.evaluation.phase3 import (
    UNGROUNDED_NAME,
    BenchmarkAbortedError,
    _build_parser,
    _failure_summary,
    baseline_claim_verdict,
    run_benchmark,
    ungrounded_claim_verdict,
)
from aletheia.evaluation.report import aggregate_reports
from aletheia.llm import FakeLLMClient, LLMError, Message

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

    # The raw paired predictions ride along for significance testing.
    assert report.gold == [Verdict.SUPPORTED, Verdict.CONTRADICTED]
    assert report.grounded_pred == [Verdict.SUPPORTED, Verdict.SUPPORTED]
    assert report.baseline_pred == [Verdict.SUPPORTED, Verdict.SUPPORTED]
    assert report.ungrounded_pred is None


async def test_baseline_parses_a_three_way_verdict() -> None:
    client = FakeLLMClient('{"verdict": "Unverifiable"}')

    verdict = await baseline_claim_verdict(client, "a claim", "some evidence")

    assert verdict is Verdict.UNVERIFIABLE


def _ablation_router(messages: Sequence[Message], json_mode: bool) -> str:
    """Route the three arms: both critics affirm, but only the grounded one must quote."""
    system = messages[0].content
    if "MUST quote" in system:  # grounded Verifier — quotes a span NOT in the evidence
        return (
            '{"verdict": "Supported", "quoted_span": "aspirin cures every disease", '
            '"reasoning": "fabricated quote"}'
        )
    if "verification critic" in system:  # ungrounded ablation arm — a bare opinion
        return '{"verdict": "Supported", "reasoning": "sounds right"}'
    return '{"verdict": "Supported"}'  # the single-LLM baseline


async def test_ablation_arm_isolates_the_span_discipline() -> None:
    # One claim whose gold label says it should be flagged. Every arm *wants* to affirm
    # it; only the grounded arm's fabricated quote is checked against the evidence and
    # downgraded — the exact mechanism H2 attributes the false-agreement gap to.
    items = [BenchmarkItem(id="1", claim="Aspirin cures every disease.", gold=Verdict.CONTRADICTED)]

    report = await run_benchmark(
        items, retrieve=_retrieve, llm=FakeLLMClient(_ablation_router), ablation=True
    )

    assert report.ungrounded is not None
    assert report.grounded.score.catch_rate == 1.0  # downgrade flagged the claim
    assert report.ungrounded.score.catch_rate == 0.0  # the opinion sailed through
    assert report.ungrounded.score.false_agreement_rate == 1.0
    assert report.ungrounded.latency.n == 1
    assert report.ungrounded.cost.total_tokens > 0
    assert report.ungrounded_pred == [Verdict.SUPPORTED]
    assert UNGROUNDED_NAME in report.render()


async def test_without_ablation_the_arm_is_absent() -> None:
    report = await run_benchmark(_items(), retrieve=_retrieve, llm=FakeLLMClient(_router))

    assert report.ungrounded is None
    assert UNGROUNDED_NAME not in report.render()


async def test_ungrounded_verdict_parses_a_bare_reply() -> None:
    client = FakeLLMClient('{"verdict": "Contradicted", "reasoning": "refuted"}')

    verdict = await ungrounded_claim_verdict(client, "a claim", "some evidence")

    assert verdict is Verdict.CONTRADICTED


async def test_repeated_runs_aggregate_to_mean_std() -> None:
    reports = [
        await run_benchmark(_items(), retrieve=_retrieve, llm=FakeLLMClient(_router))
        for _ in range(2)
    ]

    aggregated = aggregate_reports(reports)

    assert aggregated.repeats == 2
    assert aggregated.grounded.accuracy.mean == 0.5
    # The fake is deterministic, so two repeats agree exactly — no spread.
    assert aggregated.grounded.accuracy.std == 0.0


def test_cli_rejects_limit_and_sample_together(capsys: pytest.CaptureFixture[str]) -> None:
    # --limit is a head-slice for smoke runs; --sample is the seeded stratified draw for
    # headline runs. Asking for both is a contradiction the parser refuses up front.
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--claims", "claims.jsonl", "--limit", "5", "--sample", "10"])
    assert "not allowed with" in capsys.readouterr().err


def _fail_baseline_on(fragment: str):
    """A router where the grounded arm always succeeds but the baseline call fails for
    any claim containing ``fragment`` — the cross-arm case: the item must then be
    excluded from *both* systems, not just the one that errored."""

    def router(messages: Sequence[Message], json_mode: bool) -> str:
        system = messages[0].content
        if "verification critic" in system:  # the grounded Verifier
            return (
                '{"verdict": "Supported", "quoted_span": "Aspirin reduces cardiovascular '
                'risk", "reasoning": "stated in the evidence"}'
            )
        if fragment in messages[-1].content:  # the baseline call for the poisoned claim
            raise LLMError("provider timeout (scripted)")
        return '{"verdict": "Supported"}'

    return router


def _three_items() -> list[BenchmarkItem]:
    return [
        BenchmarkItem(id="1", claim="Aspirin reduces cardiovascular risk.", gold=Verdict.SUPPORTED),
        BenchmarkItem(id="2", claim="Zinc shortens colds.", gold=Verdict.CONTRADICTED),
        BenchmarkItem(id="3", claim="Aspirin thins the blood.", gold=Verdict.SUPPORTED),
    ]


async def test_a_failed_item_is_skipped_in_every_arm_and_recorded() -> None:
    report = await run_benchmark(
        _three_items(),
        retrieve=_retrieve,
        llm=FakeLLMClient(_fail_baseline_on("Zinc")),
        max_failures=5,
    )

    # Item 2 failed only in the baseline arm, yet it is excluded everywhere: the
    # paired lists cover items 1 and 3 exactly, in order.
    assert report.n_items == 2
    assert report.gold == [Verdict.SUPPORTED, Verdict.SUPPORTED]
    assert len(report.grounded_pred) == len(report.baseline_pred) == 2
    assert len(report.traces) == 2
    assert [trace.query for trace in report.traces] == [
        "Aspirin reduces cardiovascular risk.",
        "Aspirin thins the blood.",
    ]

    # The failure is recorded, not fabricated into a verdict.
    assert [failure.item_id for failure in report.failures] == ["2"]
    assert "provider timeout" in report.failures[0].error

    # The recorders were rolled back: the failed item's grounded call (which had
    # succeeded before the baseline errored) does not pollute per-query cost.
    assert report.grounded.cost.n_queries == 2
    assert report.baseline.cost.n_queries == 2
    assert report.grounded.latency.n == 2


async def test_exceeding_max_failures_aborts_with_partial_traces() -> None:
    with pytest.raises(BenchmarkAbortedError) as excinfo:
        await run_benchmark(
            _three_items(),
            retrieve=_retrieve,
            llm=FakeLLMClient(_fail_baseline_on("Zinc")),
            max_failures=0,  # zero tolerance: the first failure exceeds the cap
        )

    # Item 1 had already scored when item 2 aborted the run; its trace survives.
    assert len(excinfo.value.traces) == 1
    assert [failure.item_id for failure in excinfo.value.failures] == ["2"]
    assert "cap exceeded" in str(excinfo.value)


async def test_failure_summary_names_the_failed_items_once() -> None:
    llm = FakeLLMClient(_fail_baseline_on("Zinc"))
    reports = [
        await run_benchmark(_three_items(), retrieve=_retrieve, llm=llm, max_failures=5)
        for _ in range(2)
    ]

    # The same item failed in both repeats; the summary counts it once.
    assert _failure_summary(reports, requested=3) == "FAILED 1/3 items: [2]"


async def test_failure_summary_is_none_for_a_clean_run() -> None:
    report = await run_benchmark(_items(), retrieve=_retrieve, llm=FakeLLMClient(_router))

    assert report.failures == []
    assert _failure_summary([report], requested=2) is None
