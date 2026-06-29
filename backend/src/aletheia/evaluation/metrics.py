"""Metrics for the grounded-vs-baseline comparison.

A claim is treated as a binary decision: the system either judges it *supported* or it
*flags* it (anything other than supported). Against the gold labels this yields the two
numbers that matter for the thesis — how many genuinely unsupported claims a system
catches, and how often it wrongly flags a supported one. Both systems are always
reported together so every number is a comparison, never an absolute in a vacuum.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from aletheia.agents.contracts import Verdict
from aletheia.llm.base import TokenUsage


@dataclass(frozen=True, slots=True)
class SystemScore:
    """Aggregate scores for one system over a set of claims."""

    name: str
    n_claims: int
    n_supported: int
    n_unsupported: int
    caught_unsupported: int
    false_flags: int
    correct: int

    @property
    def catch_rate(self) -> float:
        """Fraction of genuinely unsupported claims the system flagged (recall)."""
        if self.n_unsupported == 0:
            return 1.0
        return self.caught_unsupported / self.n_unsupported

    @property
    def false_flag_rate(self) -> float:
        """Fraction of genuinely supported claims the system wrongly flagged."""
        if self.n_supported == 0:
            return 0.0
        return self.false_flags / self.n_supported

    @property
    def accuracy(self) -> float:
        """Fraction of claims labelled in agreement with the gold label."""
        if self.n_claims == 0:
            return 1.0
        return self.correct / self.n_claims


def score_system(
    name: str,
    predicted_supported: list[bool],
    gold_supported: list[bool],
) -> SystemScore:
    """Score predictions (True = judged supported) against gold labels."""
    if len(predicted_supported) != len(gold_supported):
        raise ValueError(
            f"{len(predicted_supported)} predictions for {len(gold_supported)} gold labels."
        )

    n_unsupported = 0
    caught = 0
    false_flags = 0
    correct = 0
    for pred, gold in zip(predicted_supported, gold_supported, strict=True):
        if not gold:
            n_unsupported += 1
            if not pred:  # genuinely unsupported and flagged
                caught += 1
        elif not pred:  # genuinely supported but flagged
            false_flags += 1
        if pred == gold:
            correct += 1

    return SystemScore(
        name=name,
        n_claims=len(gold_supported),
        n_supported=len(gold_supported) - n_unsupported,
        n_unsupported=n_unsupported,
        caught_unsupported=caught,
        false_flags=false_flags,
        correct=correct,
    )


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def format_comparison(scores: list[SystemScore]) -> str:
    """Render scores as an aligned, side-by-side text table."""
    name_width = max((len(score.name) for score in scores), default=12)
    header = (
        f"{'System':<{name_width}}  {'Catch rate':>16}  {'False-flag rate':>16}  {'Accuracy':>10}"
    )
    lines = [header, "-" * len(header)]
    for score in scores:
        catch = f"{score.caught_unsupported}/{score.n_unsupported} ({score.catch_rate * 100:.0f}%)"
        flag = f"{score.false_flags}/{score.n_supported} ({score.false_flag_rate * 100:.0f}%)"
        lines.append(
            f"{score.name:<{name_width}}  {catch:>16}  {flag:>16}  {_pct(score.accuracy):>10}"
        )
    return "\n".join(lines)


# --- Phase 3 metric suite -------------------------------------------------------------
#
# Phase 1 above scores a binary supported/flagged decision. The Phase 3 benchmark scores
# the pipeline's full three-valued verdict (Supported / Contradicted / Unverifiable)
# against gold labels in the same space, and adds the latency and cost dimensions the
# headline table reports. Every definition below is pure and, per EVALUATION.md §3,
# reported with the single-LLM baseline alongside.


@dataclass(frozen=True, slots=True)
class VerdictScore:
    """Three-way verdict scores for one system over a set of claims."""

    name: str
    n_claims: int
    correct: int
    n_should_flag: int  # gold is not Supported (Contradicted or Unverifiable)
    flagged: int  # of those, how many the system did not call Supported
    n_predicted_supported: int  # how many claims the system affirmed as Supported
    false_supported: int  # of those, how many gold says are not Supported

    @property
    def accuracy(self) -> float:
        """Fraction of claims whose predicted verdict exactly matches the gold verdict."""
        if self.n_claims == 0:
            return 1.0
        return self.correct / self.n_claims

    @property
    def catch_rate(self) -> float:
        """Recall on claims that should be flagged: of the claims whose gold is not
        Supported, the fraction the system did not call Supported."""
        if self.n_should_flag == 0:
            return 1.0
        return self.flagged / self.n_should_flag

    @property
    def false_agreement_rate(self) -> float:
        """Of the claims the system affirmed as Supported, the fraction gold says are not
        Supported — how often the system "agrees" a claim holds when it does not. This is
        the failure mode quoted-span grounding is meant to suppress (EVALUATION.md H2)."""
        if self.n_predicted_supported == 0:
            return 0.0
        return self.false_supported / self.n_predicted_supported


def score_verdicts(
    name: str,
    predicted: Sequence[Verdict],
    gold: Sequence[Verdict],
) -> VerdictScore:
    """Score predicted verdicts against gold verdicts in the three-valued space."""
    if len(predicted) != len(gold):
        raise ValueError(f"{len(predicted)} predictions for {len(gold)} gold labels.")

    correct = 0
    n_should_flag = 0
    flagged = 0
    n_predicted_supported = 0
    false_supported = 0
    for pred, want in zip(predicted, gold, strict=True):
        if pred == want:
            correct += 1
        if want is not Verdict.SUPPORTED:
            n_should_flag += 1
            if pred is not Verdict.SUPPORTED:
                flagged += 1
        if pred is Verdict.SUPPORTED:
            n_predicted_supported += 1
            if want is not Verdict.SUPPORTED:
                false_supported += 1

    return VerdictScore(
        name=name,
        n_claims=len(gold),
        correct=correct,
        n_should_flag=n_should_flag,
        flagged=flagged,
        n_predicted_supported=n_predicted_supported,
        false_supported=false_supported,
    )


@dataclass(frozen=True, slots=True)
class LatencyStats:
    """Wall-clock latency percentiles over a set of per-query timings, in seconds."""

    n: int
    p50: float
    p95: float
    p99: float


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (the numpy/type-7 method) over sorted values."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (rank - low)


def latency_percentiles(samples: Sequence[float]) -> LatencyStats:
    """Compute p50/p95/p99 latency from per-query wall-clock samples (seconds)."""
    if not samples:
        raise ValueError("latency_percentiles needs at least one sample.")
    ordered = sorted(samples)
    return LatencyStats(
        n=len(ordered),
        p50=_percentile(ordered, 50),
        p95=_percentile(ordered, 95),
        p99=_percentile(ordered, 99),
    )


@dataclass(frozen=True, slots=True)
class CostStats:
    """Token cost aggregated over a run, reported per query (free-tier accounting)."""

    n_queries: int
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def tokens_per_query(self) -> float:
        if self.n_queries == 0:
            return 0.0
        return self.total_tokens / self.n_queries


def cost_from_usages(usages: Sequence[TokenUsage]) -> CostStats:
    """Aggregate per-query token usage into a run-level cost summary."""
    return CostStats(
        n_queries=len(usages),
        prompt_tokens=sum(usage.prompt_tokens for usage in usages),
        completion_tokens=sum(usage.completion_tokens for usage in usages),
    )


@dataclass(frozen=True, slots=True)
class MeanStd:
    """A metric summarised across seeded repeats: mean and sample standard deviation."""

    mean: float
    std: float
    n: int

    def __str__(self) -> str:
        return f"{self.mean:.3f} ± {self.std:.3f}"


def summarize(values: Sequence[float]) -> MeanStd:
    """Summarise a metric measured over several seeded runs as mean ± std.

    A single run has no spread, so its standard deviation is reported as zero rather than
    undefined; this keeps a one-seed smoke run renderable.
    """
    if not values:
        raise ValueError("summarize needs at least one value.")
    return MeanStd(
        mean=statistics.fmean(values),
        std=statistics.stdev(values) if len(values) > 1 else 0.0,
        n=len(values),
    )
