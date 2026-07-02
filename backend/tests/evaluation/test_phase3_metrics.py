"""Tests for the Phase 3 metric suite — pure functions over measurements.

These cover the three-valued verdict scoring and the latency, cost, and mean ± std
aggregations that feed the headline benchmark table.
"""

from __future__ import annotations

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.metrics import (
    cost_from_usages,
    discordant_pairs,
    latency_percentiles,
    mcnemar_exact,
    paired_bootstrap_delta,
    score_verdicts,
    summarize,
)
from aletheia.llm import TokenUsage


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


# --- Paired significance ----------------------------------------------------------------

S, C, U = Verdict.SUPPORTED, Verdict.CONTRADICTED, Verdict.UNVERIFIABLE


def test_discordant_pairs_counts_only_one_sided_correctness() -> None:
    gold = [S, C, U, S]
    pred_a = [S, S, U, C]  # right, wrong, right, wrong
    pred_b = [S, C, S, C]  # right, right, wrong, wrong

    # Item 2: only B right; item 3: only A right; items 1 and 4 are concordant.
    assert discordant_pairs(pred_a, pred_b, gold) == (1, 1)


def test_discordant_pairs_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="differ in length"):
        discordant_pairs([S], [S, S], [S, S])


def test_mcnemar_exact_matches_hand_computed_binomial_tails() -> None:
    # n=9 discordant, min side 1: p = 2 * (C(9,0) + C(9,1)) / 2^9 = 20/512.
    assert mcnemar_exact(1, 8) == pytest.approx(20 / 512)
    # n=5, one-sided split 0/5: p = 2 * 1/32.
    assert mcnemar_exact(0, 5) == pytest.approx(2 / 32)


def test_mcnemar_exact_is_inconclusive_on_ties_and_no_evidence() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 3) == 1.0


def test_mcnemar_exact_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        mcnemar_exact(-1, 2)


def _accuracy(predicted: list[Verdict], gold: list[Verdict]) -> float:
    return score_verdicts("_", predicted, gold).accuracy


def test_paired_bootstrap_delta_is_exact_when_one_system_dominates() -> None:
    # A is wrong on every claim, B right on every claim: every resample's accuracy
    # delta is exactly +1, so the interval collapses to the point.
    gold = [S, C, U, S, C, U]
    pred_a = [C, S, S, C, S, S]
    pred_b = list(gold)

    ci = paired_bootstrap_delta(pred_a, pred_b, gold, _accuracy, n_resamples=200, seed=7)

    assert ci.point == pytest.approx(1.0)
    assert ci.low == pytest.approx(1.0)
    assert ci.high == pytest.approx(1.0)


def test_paired_bootstrap_delta_is_zero_for_identical_systems() -> None:
    gold = [S, C, U, S]
    pred = [S, S, U, C]

    ci = paired_bootstrap_delta(pred, list(pred), gold, _accuracy, n_resamples=100, seed=3)

    assert (ci.point, ci.low, ci.high) == (0.0, 0.0, 0.0)


def test_paired_bootstrap_delta_is_deterministic_under_a_seed() -> None:
    gold = [S, C, U, S, C, U, S, C]
    pred_a = [S, S, U, S, S, U, C, C]
    pred_b = [S, C, U, C, C, S, S, C]

    first = paired_bootstrap_delta(pred_a, pred_b, gold, _accuracy, n_resamples=300, seed=11)
    second = paired_bootstrap_delta(pred_a, pred_b, gold, _accuracy, n_resamples=300, seed=11)
    other_seed = paired_bootstrap_delta(pred_a, pred_b, gold, _accuracy, n_resamples=300, seed=12)

    assert (first.low, first.high) == (second.low, second.high)
    assert first.point == other_seed.point  # the point estimate ignores the seed
    assert first.low <= first.point <= first.high


def test_paired_bootstrap_delta_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError, match="differ in length"):
        paired_bootstrap_delta([S], [S, S], [S, S], _accuracy)
    with pytest.raises(ValueError, match="at least one claim"):
        paired_bootstrap_delta([], [], [], _accuracy)
    with pytest.raises(ValueError, match="n_resamples"):
        paired_bootstrap_delta([S], [S], [S], _accuracy, n_resamples=0)
