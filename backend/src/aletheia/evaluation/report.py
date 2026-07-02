"""Seeded aggregation and the EVALUATION.md headline table.

A benchmark run is non-deterministic, so the headline numbers are reported as mean ±
standard deviation across several seeded repeats (EVALUATION.md §5). This module
aggregates the per-repeat :class:`BenchmarkReport`s into one :class:`AggregatedReport`
and renders it as the §6.2 markdown table, written between markers in ``EVALUATION.md``
so a live run refreshes the numbers in place.

It depends on the phase3 report types for *annotations only* (a ``TYPE_CHECKING`` import),
reading their attributes at runtime — so there is no import cycle with the runner.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.metrics import (
    MeanStd,
    discordant_pairs,
    mcnemar_exact,
    paired_bootstrap_delta,
    score_verdicts,
    summarize,
)

if TYPE_CHECKING:
    from aletheia.evaluation.phase3 import BenchmarkReport, SystemReport

#: Markers in EVALUATION.md between which the generated §6.2 table is written.
SECTION_BEGIN = "<!-- PHASE3:BEGIN -->"
SECTION_END = "<!-- PHASE3:END -->"


@dataclass(frozen=True, slots=True)
class AggregatedSystemReport:
    """One system's metrics aggregated across seeded repeats."""

    name: str
    accuracy: MeanStd
    catch_rate: MeanStd
    false_agreement_rate: MeanStd
    latency_p50: float
    latency_p95: float
    latency_p99: float
    tokens_per_query: float


@dataclass(frozen=True, slots=True)
class AggregatedReport:
    """The systems aggregated across repeats — the basis for the headline table.

    ``ungrounded`` is present only when every repeat ran the H2 ablation arm; the
    reporting order is everywhere baseline → ungrounded → grounded.
    """

    n_items: int
    repeats: int
    baseline: AggregatedSystemReport
    grounded: AggregatedSystemReport
    ungrounded: AggregatedSystemReport | None = None


def _aggregate_system(systems: Sequence[SystemReport]) -> AggregatedSystemReport:
    """Aggregate one system's per-repeat reports: rates as mean ± std, the rest averaged."""
    return AggregatedSystemReport(
        name=systems[0].name,
        accuracy=summarize([s.score.accuracy for s in systems]),
        catch_rate=summarize([s.score.catch_rate for s in systems]),
        false_agreement_rate=summarize([s.score.false_agreement_rate for s in systems]),
        latency_p50=statistics.fmean([s.latency.p50 for s in systems]),
        latency_p95=statistics.fmean([s.latency.p95 for s in systems]),
        latency_p99=statistics.fmean([s.latency.p99 for s in systems]),
        tokens_per_query=statistics.fmean([s.cost.tokens_per_query for s in systems]),
    )


def aggregate_reports(reports: Sequence[BenchmarkReport]) -> AggregatedReport:
    """Aggregate per-repeat benchmark reports into one mean ± std summary.

    The ablation arm is aggregated only when *every* repeat ran it — a mixed set of
    two- and three-arm repeats would silently average incomparable runs, so the arm
    is dropped from the summary instead.
    """
    if not reports:
        raise ValueError("aggregate_reports needs at least one report.")
    ungrounded_runs = [report.ungrounded for report in reports]
    ungrounded = (
        _aggregate_system([run for run in ungrounded_runs if run is not None])
        if all(run is not None for run in ungrounded_runs)
        else None
    )
    return AggregatedReport(
        n_items=reports[0].n_items,
        repeats=len(reports),
        baseline=_aggregate_system([report.baseline for report in reports]),
        grounded=_aggregate_system([report.grounded for report in reports]),
        ungrounded=ungrounded,
    )


def _pct(stat: MeanStd) -> str:
    return f"{stat.mean * 100:.1f}% ± {stat.std * 100:.1f}%"


def _row(system: AggregatedSystemReport) -> str:
    latency = f"{system.latency_p50:.3f} / {system.latency_p95:.3f} / {system.latency_p99:.3f}"
    return (
        f"| {system.name} | {_pct(system.accuracy)} | {_pct(system.catch_rate)} | "
        f"{_pct(system.false_agreement_rate)} | {latency} | {system.tokens_per_query:.1f} |"
    )


def render_markdown(report: AggregatedReport) -> str:
    """Render the §6.2 headline table as markdown (mean ± std over the seeded repeats)."""
    rows = [_row(report.baseline)]
    if report.ungrounded is not None:
        rows.append(_row(report.ungrounded))
    rows.append(_row(report.grounded))
    return "\n".join(
        [
            f"_SciFact · {report.n_items} claims · {report.repeats} seeded run"
            f"{'s' if report.repeats != 1 else ''} · mean ± std._",
            "",
            "| System | Verif. accuracy | Catch rate | False-agreement | "
            "Latency p50/p95/p99 (s) | Tokens/query |",
            "| --- | --- | --- | --- | --- | --- |",
            *rows,
        ]
    )


def _catch_rate(predicted: Sequence[Verdict], gold: Sequence[Verdict]) -> float:
    return score_verdicts("_", predicted, gold).catch_rate


def _false_agreement(predicted: Sequence[Verdict], gold: Sequence[Verdict]) -> float:
    return score_verdicts("_", predicted, gold).false_agreement_rate


def _pp(value: float) -> str:
    """A rate delta as signed percentage points."""
    return f"{value * 100:+.1f}"


# Mirrors paired_bootstrap_delta's shape: the paired inputs plus explicit knobs.
def _significance_line(  # noqa: PLR0913
    label: str,
    pred_a: Sequence[Verdict],
    pred_b: Sequence[Verdict],
    gold: Sequence[Verdict],
    *,
    n_resamples: int,
    seed: int,
) -> str:
    """One comparison's footnote line: McNemar on accuracy + bootstrap CIs on the rates.

    ``pred_b`` is the system the deltas favour when positive (here always the grounded
    verifier); a *negative* false-agreement delta is the desired direction.
    """
    a_only, b_only = discordant_pairs(pred_a, pred_b, gold)
    p = mcnemar_exact(a_only, b_only)
    catch = paired_bootstrap_delta(
        pred_a, pred_b, gold, _catch_rate, n_resamples=n_resamples, seed=seed
    )
    agree = paired_bootstrap_delta(
        pred_a, pred_b, gold, _false_agreement, n_resamples=n_resamples, seed=seed
    )
    return (
        f"_{label} (paired, n={len(gold)}): accuracy McNemar exact p = {p:.3f} "
        f"({a_only + b_only} discordant); catch-rate Δ {_pp(catch.point)} pp, "
        f"95% CI [{_pp(catch.low)}, {_pp(catch.high)}]; "
        f"false-agreement Δ {_pp(agree.point)} pp, "
        f"95% CI [{_pp(agree.low)}, {_pp(agree.high)}]._"
    )


def render_significance(
    report: BenchmarkReport, *, n_resamples: int = 10_000, seed: int = 7
) -> str | None:
    """Render the paired-significance footnote from one repeat's raw predictions.

    Uses the per-claim verdicts carried on the report (H1: grounded vs baseline; H2:
    grounded vs the ungrounded ablation arm, when it ran). Returns ``None`` for reports
    that carry no predictions, so older callers and hand-built reports stay renderable.
    Deltas are grounded-minus-comparator: catch-rate should be positive, false-agreement
    negative.
    """
    if not report.gold:
        return None
    lines = [
        _significance_line(
            "Grounded vs baseline (H1)",
            report.baseline_pred,
            report.grounded_pred,
            report.gold,
            n_resamples=n_resamples,
            seed=seed,
        )
    ]
    if report.ungrounded_pred is not None:
        lines.append(
            _significance_line(
                "Grounded vs ungrounded ablation (H2)",
                report.ungrounded_pred,
                report.grounded_pred,
                report.gold,
                n_resamples=n_resamples,
                seed=seed,
            )
        )
    lines.append(
        f"_Significance computed on the first repeat's paired per-claim predictions; "
        f"percentile bootstrap with {n_resamples:,} resamples, seed {seed}._"
    )
    return "\n".join(lines)


def update_evaluation_md(path: str | Path, section: str) -> None:
    """Replace the content between the PHASE3 markers in ``path`` with ``section``."""
    text = Path(path).read_text(encoding="utf-8")
    if SECTION_BEGIN not in text or SECTION_END not in text:
        raise ValueError(f"{path} is missing the {SECTION_BEGIN} / {SECTION_END} markers.")
    head = text[: text.index(SECTION_BEGIN) + len(SECTION_BEGIN)]
    tail = text[text.index(SECTION_END) :]
    Path(path).write_text(f"{head}\n{section}\n{tail}", encoding="utf-8")
