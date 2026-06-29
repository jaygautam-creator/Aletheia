"""Tests for the Phase 3 metric suite — pure functions over measurements.

These cover the three-valued verdict scoring and the latency, cost, and mean ± std
aggregations that feed the headline benchmark table.
"""

from __future__ import annotations

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.metrics import (
    TokenUsage,
    cost_from_usages,
    latency_percentiles,
    score_verdicts,
    summarize,
)


def test_score_verdicts_measures_accuracy_catch_and_false_agreement() -> None:
    predicted = [Verdict.SUPPORTED, Verdict.SUPPORTED, Verdict.UNVERIFIABLE, Verdict.CONTRADICTED]
    gold = [Verdict.SUPPORTED, Verdict.CONTRADICTED, Verdict.UNVERIFIABLE, Verdict.CONTRADICTED]

    score = score_verdicts("system", predicted, gold)

    # 3 of 4 verdicts match exactly.
    assert score.accuracy == pytest.approx(0.75)
    # Of 3 claims that should be flagged (gold != Supported), 2 were not called Supported.
    assert score.catch_rate == pytest.approx(2 / 3)
    # Of 2 claims affirmed Supported, 1 was wrong (gold Contradicted) -> false agreement.
    assert score.false_agreement_rate == pytest.approx(0.5)


def test_score_verdicts_handles_degenerate_denominators() -> None:
    # All Supported gold/pred: nothing to flag, nothing falsely agreed.
    score = score_verdicts("s", [Verdict.SUPPORTED], [Verdict.SUPPORTED])
    assert score.accuracy == pytest.approx(1.0)
    assert score.catch_rate == pytest.approx(1.0)  # no flag-worthy claims
    assert score.false_agreement_rate == pytest.approx(0.0)


def test_score_verdicts_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="2 predictions for 1 gold"):
        score_verdicts("s", [Verdict.SUPPORTED, Verdict.SUPPORTED], [Verdict.SUPPORTED])


def test_latency_percentiles_interpolate_between_samples() -> None:
    stats = latency_percentiles([10.0, 20.0, 30.0, 40.0, 50.0])

    assert stats.n == 5
    assert stats.p50 == pytest.approx(30.0)
    assert stats.p95 == pytest.approx(48.0)
    assert stats.p99 == pytest.approx(49.6)


def test_latency_percentiles_with_a_single_sample() -> None:
    stats = latency_percentiles([0.42])
    assert (stats.p50, stats.p95, stats.p99) == (0.42, 0.42, 0.42)


def test_latency_percentiles_rejects_no_samples() -> None:
    with pytest.raises(ValueError, match="at least one sample"):
        latency_percentiles([])


def test_cost_from_usages_sums_tokens_and_averages_per_query() -> None:
    cost = cost_from_usages([TokenUsage(100, 50), TokenUsage(200, 100)])

    assert cost.prompt_tokens == 300
    assert cost.completion_tokens == 150
    assert cost.total_tokens == 450
    assert cost.tokens_per_query == pytest.approx(225.0)


def test_cost_from_no_usages_is_zero() -> None:
    cost = cost_from_usages([])
    assert cost.total_tokens == 0
    assert cost.tokens_per_query == pytest.approx(0.0)


def test_summarize_reports_mean_and_sample_std() -> None:
    summary = summarize([0.8, 0.9, 1.0])

    assert summary.mean == pytest.approx(0.9)
    assert summary.std == pytest.approx(0.1)
    assert summary.n == 3
    assert str(summary) == "0.900 ± 0.100"


def test_summarize_single_value_has_zero_spread() -> None:
    summary = summarize([0.5])
    assert summary.mean == pytest.approx(0.5)
    assert summary.std == pytest.approx(0.0)


def test_summarize_rejects_no_values() -> None:
    with pytest.raises(ValueError, match="at least one value"):
        summarize([])
