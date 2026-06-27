"""Tests for the comparison metrics."""

from __future__ import annotations

import pytest

from aletheia.evaluation import format_comparison, score_system


def test_perfect_grounded_scores() -> None:
    # gold: claim 0 supported, claims 1 and 2 unsupported (planted).
    gold = [True, False, False]
    predicted = [True, False, False]  # flags both planted claims, keeps the real one

    score = score_system("grounded", predicted, gold)

    assert score.n_claims == 3
    assert score.n_unsupported == 2
    assert score.caught_unsupported == 2
    assert score.catch_rate == 1.0
    assert score.false_flags == 0
    assert score.false_flag_rate == 0.0
    assert score.accuracy == 1.0


def test_baseline_that_misses_planted_claims() -> None:
    gold = [True, False, False]
    predicted = [True, True, True]  # rubber-stamps everything

    score = score_system("baseline", predicted, gold)

    assert score.caught_unsupported == 0
    assert score.catch_rate == 0.0
    assert score.accuracy == pytest.approx(1 / 3)


def test_false_flag_is_counted() -> None:
    gold = [True, True, False]
    predicted = [False, True, False]  # wrongly flags a supported claim

    score = score_system("trigger-happy", predicted, gold)

    assert score.false_flags == 1
    assert score.false_flag_rate == 0.5
    assert score.caught_unsupported == 1
    assert score.catch_rate == 1.0


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="predictions for"):
        score_system("bad", [True], [True, False])


def test_format_comparison_includes_both_systems() -> None:
    baseline = score_system("Single-LLM baseline", [True, True], [True, False])
    grounded = score_system("Aletheia", [True, False], [True, False])

    table = format_comparison([baseline, grounded])

    assert "Single-LLM baseline" in table
    assert "Aletheia" in table
    assert "Catch rate" in table
