"""Tests for seeded aggregation and the EVALUATION.md table generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.metrics import CostStats, LatencyStats, VerdictScore
from aletheia.evaluation.phase3 import BenchmarkReport, SystemReport
from aletheia.evaluation.report import (
    SECTION_BEGIN,
    SECTION_END,
    aggregate_reports,
    frontend_results,
    render_markdown,
    render_significance,
    update_evaluation_md,
    write_frontend_json,
)


def _system(name: str, *, accuracy: float, p50: float, tokens: int) -> SystemReport:
    return SystemReport(
        name=name,
        score=VerdictScore(
            name=name,
            n_claims=10,
            correct=round(accuracy * 10),
            n_should_flag=10,
            flagged=5,
            n_predicted_supported=10,
            false_supported=2,
        ),
        latency=LatencyStats(n=10, p50=p50, p95=p50 * 2, p99=p50 * 3),
        cost=CostStats(n_queries=10, prompt_tokens=tokens * 10, completion_tokens=0),
    )


def _report(
    *, grounded_acc: float, baseline_acc: float, ungrounded_acc: float | None = None
) -> BenchmarkReport:
    return BenchmarkReport(
        n_items=10,
        grounded=_system("Aletheia (grounded verifier)", accuracy=grounded_acc, p50=0.2, tokens=30),
        baseline=_system("Single-LLM baseline", accuracy=baseline_acc, p50=0.1, tokens=20),
        traces=[],
        ungrounded=(
            _system(
                "Multi-agent, ungrounded (ablation)", accuracy=ungrounded_acc, p50=0.15, tokens=25
            )
            if ungrounded_acc is not None
            else None
        ),
    )


def test_aggregate_reports_reports_mean_and_std() -> None:
    aggregated = aggregate_reports(
        [_report(grounded_acc=0.8, baseline_acc=0.6), _report(grounded_acc=0.9, baseline_acc=0.7)]
    )

    assert aggregated.repeats == 2
    assert aggregated.n_items == 10
    assert aggregated.grounded.accuracy.mean == pytest.approx(0.85)
    assert aggregated.grounded.accuracy.std == pytest.approx(0.0707, abs=1e-3)
    assert aggregated.baseline.accuracy.mean == pytest.approx(0.65)
    # Latency and cost are averaged across repeats (identical here).
    assert aggregated.grounded.latency_p50 == pytest.approx(0.2)
    assert aggregated.grounded.tokens_per_query == pytest.approx(30.0)


def test_aggregate_reports_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one report"):
        aggregate_reports([])


def test_aggregate_includes_the_ablation_arm_when_every_repeat_ran_it() -> None:
    aggregated = aggregate_reports(
        [
            _report(grounded_acc=0.8, baseline_acc=0.6, ungrounded_acc=0.6),
            _report(grounded_acc=0.9, baseline_acc=0.7, ungrounded_acc=0.8),
        ]
    )

    assert aggregated.ungrounded is not None
    assert aggregated.ungrounded.accuracy.mean == pytest.approx(0.7)


def test_aggregate_drops_the_ablation_arm_when_repeats_are_mixed() -> None:
    # Averaging a two-arm repeat with a three-arm repeat would compare incomparable
    # runs, so the arm is dropped from the summary rather than silently averaged.
    aggregated = aggregate_reports(
        [
            _report(grounded_acc=0.8, baseline_acc=0.6, ungrounded_acc=0.6),
            _report(grounded_acc=0.9, baseline_acc=0.7),
        ]
    )

    assert aggregated.ungrounded is None


def test_render_markdown_orders_the_ablation_row_between_baseline_and_grounded() -> None:
    markdown = render_markdown(
        aggregate_reports([_report(grounded_acc=0.8, baseline_acc=0.6, ungrounded_acc=0.7)])
    )

    baseline_at = markdown.index("| Single-LLM baseline |")
    ungrounded_at = markdown.index("| Multi-agent, ungrounded (ablation) |")
    grounded_at = markdown.index("| Aletheia (grounded verifier) |")
    assert baseline_at < ungrounded_at < grounded_at


def test_render_markdown_has_both_rows_and_mean_std() -> None:
    markdown = render_markdown(aggregate_reports([_report(grounded_acc=0.8, baseline_acc=0.6)]))

    assert "| Single-LLM baseline |" in markdown
    assert "| Aletheia (grounded verifier) |" in markdown
    assert "± " in markdown  # rates carry a spread
    assert "Verif. accuracy" in markdown


S, C, U = Verdict.SUPPORTED, Verdict.CONTRADICTED, Verdict.UNVERIFIABLE


def _report_with_predictions(*, ablation: bool) -> BenchmarkReport:
    """A report carrying raw paired predictions, as run_benchmark now produces."""
    base = _report(grounded_acc=0.8, baseline_acc=0.6, ungrounded_acc=0.7 if ablation else None)
    return BenchmarkReport(
        n_items=4,
        grounded=base.grounded,
        baseline=base.baseline,
        traces=[],
        ungrounded=base.ungrounded,
        gold=[S, C, U, C],
        baseline_pred=[S, S, S, S],  # affirms everything — misses both flag-worthy claims
        grounded_pred=[S, C, U, C],  # matches gold exactly
        ungrounded_pred=[S, S, C, S] if ablation else None,
    )


def test_render_significance_reports_both_hypotheses() -> None:
    footnote = render_significance(_report_with_predictions(ablation=True), n_resamples=100)

    assert footnote is not None
    assert "Grounded vs baseline (H1)" in footnote
    assert "Grounded vs ungrounded ablation (H2)" in footnote
    assert "McNemar exact p" in footnote
    assert "95% CI" in footnote
    assert "n=4" in footnote
    assert "seed 7" in footnote  # the default seed is stated for reproducibility


def test_render_significance_omits_h2_without_the_ablation_arm() -> None:
    footnote = render_significance(_report_with_predictions(ablation=False), n_resamples=100)

    assert footnote is not None
    assert "(H1)" in footnote
    assert "(H2)" not in footnote


def test_render_significance_is_none_for_reports_without_predictions() -> None:
    assert render_significance(_report(grounded_acc=0.8, baseline_acc=0.6)) is None


def test_update_evaluation_md_replaces_only_between_markers(tmp_path: Path) -> None:
    doc = tmp_path / "EVALUATION.md"
    doc.write_text(f"intro\n\n{SECTION_BEGIN}\nold table\n{SECTION_END}\n\noutro\n", "utf-8")

    update_evaluation_md(doc, "NEW SECTION")

    text = doc.read_text("utf-8")
    assert "NEW SECTION" in text
    assert "old table" not in text
    assert SECTION_BEGIN in text and SECTION_END in text
    assert text.startswith("intro")
    assert text.rstrip().endswith("outro")


def test_update_evaluation_md_requires_the_markers(tmp_path: Path) -> None:
    doc = tmp_path / "x.md"
    doc.write_text("no markers here", "utf-8")

    with pytest.raises(ValueError, match="markers"):
        update_evaluation_md(doc, "x")


def test_frontend_results_carries_provenance_and_systems_in_order() -> None:
    data = frontend_results(
        aggregate_reports([_report(grounded_acc=0.75, baseline_acc=0.65, ungrounded_acc=0.7)]),
        model="groq:llama-3.1-8b-instant",
        seed=7,
        run_date="2026-06-30",
    )

    assert data["dataset"] == "SciFact dev"
    assert data["n"] == 10
    assert data["seed"] == 7
    assert data["model"] == "groq:llama-3.1-8b-instant"
    assert data["date"] == "2026-06-30"
    # Systems in reporting order: baseline → ungrounded → grounded.
    names = [s["name"] for s in data["systems"]]
    assert names == [
        "Single-LLM baseline",
        "Multi-agent, ungrounded (ablation)",
        "Aletheia (grounded verifier)",
    ]
    # Rates are percentages, one decimal (the _report helper quantizes to tenths).
    assert data["systems"][2]["accuracy"] == 80.0


def test_frontend_results_omits_the_ablation_arm_when_absent() -> None:
    data = frontend_results(
        aggregate_reports([_report(grounded_acc=0.75, baseline_acc=0.65)]),
        model="fake:1",
        seed=1,
    )

    assert [s["name"] for s in data["systems"]] == [
        "Single-LLM baseline",
        "Aletheia (grounded verifier)",
    ]


def test_write_frontend_json_round_trips(tmp_path: Path) -> None:
    out = tmp_path / "benchmark-results.json"
    write_frontend_json(
        out,
        aggregate_reports([_report(grounded_acc=0.75, baseline_acc=0.65)]),
        model="fake:1",
        seed=7,
    )

    loaded = json.loads(out.read_text("utf-8"))
    assert loaded["systems"][0]["name"] == "Single-LLM baseline"
    assert out.read_text("utf-8").endswith("\n")
