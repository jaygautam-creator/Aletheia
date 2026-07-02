"""Tests for seeded aggregation and the EVALUATION.md table generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from aletheia.evaluation.metrics import CostStats, LatencyStats, VerdictScore
from aletheia.evaluation.phase3 import BenchmarkReport, SystemReport
from aletheia.evaluation.report import (
    SECTION_BEGIN,
    SECTION_END,
    aggregate_reports,
    render_markdown,
    update_evaluation_md,
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
