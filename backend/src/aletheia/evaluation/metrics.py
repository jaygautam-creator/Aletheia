"""Metrics for the grounded-vs-baseline comparison.

A claim is treated as a binary decision: the system either judges it *supported* or it
*flags* it (anything other than supported). Against the gold labels this yields the two
numbers that matter for the thesis — how many genuinely unsupported claims a system
catches, and how often it wrongly flags a supported one. Both systems are always
reported together so every number is a comparison, never an absolute in a vacuum.
"""

from __future__ import annotations

from dataclasses import dataclass


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
