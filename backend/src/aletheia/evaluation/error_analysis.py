"""Error analysis for the grounded arm's Phase 3 benchmark misses.

EVALUATION.md §6.2 reports the honest headline: evidence-grounded verification lifts
the hallucination-catch rate over a single-LLM baseline, but leaves *aggregate
verification accuracy* flat. That caveat is only defensible if we can say **why** —
which this module does, by joining a finished run's grounded traces back to the SciFact
gold labels and tagging every miss by its cause:

* **retrieval miss** — the abstract the gold label cites never reached the verifier
  (it was not among the retrieved evidence), so the claim could only come back
  ``Unverifiable``. The fault is the retriever's, not the verifier's.
* **verifier abstention** — the cited abstract *was* retrieved, yet the verifier still
  returned ``Unverifiable``: it would not commit to a verbatim span. This is the
  quoted-span discipline trading a genuine ``Supported``/``Contradicted`` for caution —
  the mechanism behind the flat accuracy.
* **wrong direction** — the verifier took the opposite stance to the gold label
  (``Supported`` ↔ ``Contradicted``): a genuine disagreement or a subtle gold case.
* **false grounding** — the gold label is ``Unverifiable`` (SciFact NotEnoughInfo) yet
  the verifier affirmed or refuted it anyway, quoting a span that does not actually
  settle the claim.

It reads a run's traces (written by :mod:`aletheia.evaluation.trace`) and the *same*
seeded sample the run scored, and makes **no** LLM or database calls — it is pure,
offline, reproducible post-hoc analysis, exactly like the metrics it explains.

    uv --directory backend run python -m aletheia.evaluation.error_analysis \\
        --claims data/scifact/claims_dev.jsonl --sample 100 --seed 7 \\
        --traces runs/scifact.jsonl
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from aletheia.agents.contracts import GROUNDED_VERDICTS, Verdict
from aletheia.evaluation.benchmark import (
    BenchmarkItem,
    load_scifact_claims,
    stratified_sample,
)
from aletheia.evaluation.trace import RunTrace, read_traces


class Category(StrEnum):
    """The diagnosis assigned to one scored item (one correct outcome, four miss causes)."""

    CORRECT = "correct"
    RETRIEVAL_MISS = "retrieval_miss"
    VERIFIER_ABSTENTION = "verifier_abstention"
    WRONG_DIRECTION = "wrong_direction"
    FALSE_GROUNDING = "false_grounding"


#: Human-readable gloss for each category, shown in the rendered report.
CATEGORY_LABELS: dict[Category, str] = {
    Category.CORRECT: "Correct",
    Category.RETRIEVAL_MISS: "Retrieval miss (cited abstract not retrieved → Unverifiable)",
    Category.VERIFIER_ABSTENTION: "Verifier abstention (evidence present, no span quoted)",
    Category.WRONG_DIRECTION: "Wrong direction (Supported ↔ Contradicted)",
    Category.FALSE_GROUNDING: "False grounding (gold Unverifiable, verdict asserts)",
}

#: The four miss categories, in the order the report lists them (most benign to most severe:
#: an upstream retrieval gap, then over-caution, then two substantive verifier errors).
MISS_CATEGORIES: tuple[Category, ...] = (
    Category.RETRIEVAL_MISS,
    Category.VERIFIER_ABSTENTION,
    Category.WRONG_DIRECTION,
    Category.FALSE_GROUNDING,
)


def categorize(gold: Verdict, predicted: Verdict, *, retrieved_gold: bool) -> Category:
    """Classify one item's outcome from its gold label, verdict, and retrieval success.

    ``retrieved_gold`` is whether every abstract the gold label cites was among the
    evidence actually retrieved for the claim — it is what separates a retrieval miss
    (the verifier never saw the evidence) from a verifier abstention (it did, and still
    declined). The four miss branches are mutually exclusive and exhaustive.
    """
    if predicted == gold:
        return Category.CORRECT
    if gold in GROUNDED_VERDICTS:
        if predicted == Verdict.UNVERIFIABLE:
            return Category.RETRIEVAL_MISS if not retrieved_gold else Category.VERIFIER_ABSTENTION
        return Category.WRONG_DIRECTION  # asserted the opposite stance
    return Category.FALSE_GROUNDING  # gold Unverifiable, verdict asserts a stance


@dataclass(frozen=True, slots=True)
class ItemDiagnosis:
    """One scored item joined to its gold label and tagged with a :class:`Category`."""

    item_id: str
    claim: str
    gold: Verdict
    predicted: Verdict
    retrieved_gold: bool
    category: Category
    quoted_span: str | None


@dataclass(frozen=True, slots=True)
class ErrorAnalysis:
    """The categorized diagnoses for a run, plus any items the traces did not cover.

    ``missing`` names sampled items with no matching trace — expected to be empty for a
    clean run (failed items are excluded from a run's traces), but surfaced rather than
    hidden so a mismatched (claims, sample, seed) ↔ traces pairing fails visibly.
    """

    diagnoses: list[ItemDiagnosis]
    missing: list[str]

    @property
    def n_scored(self) -> int:
        return len(self.diagnoses)

    @property
    def n_correct(self) -> int:
        return sum(1 for d in self.diagnoses if d.category is Category.CORRECT)

    @property
    def accuracy(self) -> float:
        return self.n_correct / self.n_scored if self.diagnoses else 0.0

    def counts(self) -> Counter[Category]:
        """Item count per category across the whole run."""
        return Counter(d.category for d in self.diagnoses)

    def by_gold(self, gold: Verdict) -> Counter[Category]:
        """Item count per category among items whose gold label is ``gold``."""
        return Counter(d.category for d in self.diagnoses if d.gold is gold)

    def examples(self, category: Category, limit: int) -> list[ItemDiagnosis]:
        """Up to ``limit`` diagnoses in a category, for illustrative quotes in the report."""
        picked = [d for d in self.diagnoses if d.category is category]
        return picked[:limit]


def _retrieved_gold(item: BenchmarkItem, trace: RunTrace) -> bool:
    """Whether every abstract the gold label cites was among the retrieved evidence.

    An item with no cited documents (a NotEnoughInfo claim) is vacuously satisfied — its
    gold label depends on no abstract, so retrieval cannot have missed one.
    """
    if not item.cited_doc_ids:
        return True
    retrieved = {span.external_id for span in trace.evidence}
    return all(doc_id in retrieved for doc_id in item.cited_doc_ids)


def diagnose(items: Sequence[BenchmarkItem], traces: Sequence[RunTrace]) -> ErrorAnalysis:
    """Join ``items`` to ``traces`` by claim text and diagnose each scored item.

    Traces are keyed by their claim (the grounded arm records one verdict per claim), so
    the join is order-independent: the analysis reproduces regardless of run order. Items
    with no matching trace are reported in :attr:`ErrorAnalysis.missing`, not silently
    dropped.
    """
    by_claim = {trace.query: trace for trace in traces}
    diagnoses: list[ItemDiagnosis] = []
    missing: list[str] = []
    for item in items:
        trace = by_claim.get(item.claim)
        if trace is None:
            missing.append(item.id)
            continue
        verdict_trace = trace.verdicts[0]
        predicted = Verdict(verdict_trace.verdict)
        retrieved_gold = _retrieved_gold(item, trace)
        diagnoses.append(
            ItemDiagnosis(
                item_id=item.id,
                claim=item.claim,
                gold=item.gold,
                predicted=predicted,
                retrieved_gold=retrieved_gold,
                category=categorize(item.gold, predicted, retrieved_gold=retrieved_gold),
                quoted_span=verdict_trace.quoted_span,
            )
        )
    return ErrorAnalysis(diagnoses=diagnoses, missing=missing)


def _pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator else "—"


def render_markdown(analysis: ErrorAnalysis, *, examples: int = 3) -> str:
    """Render the analysis as the Markdown block that drops into EVALUATION.md §6.2."""
    n = analysis.n_scored
    counts = analysis.counts()
    lines: list[str] = []
    lines.append(
        f"Grounded-arm error analysis · {n} scored claims · accuracy {_pct(analysis.n_correct, n)}."
    )
    lines.append("")

    # 1) Outcome breakdown across the whole run.
    lines.append("| Outcome | Claims | Share |")
    lines.append("| --- | ---: | ---: |")
    for category in (Category.CORRECT, *MISS_CATEGORIES):
        count = counts.get(category, 0)
        lines.append(f"| {CATEGORY_LABELS[category]} | {count} | {_pct(count, n)} |")
    lines.append("")

    # 2) Where the errors fall by gold label — this is what explains the flat accuracy.
    miss_headers = " | ".join(c.value for c in MISS_CATEGORIES)
    miss_rule = " | ".join("---:" for _ in MISS_CATEGORIES)
    lines.append(f"| Gold label | n | Correct | {miss_headers} |")
    lines.append(f"| --- | ---: | ---: | {miss_rule} |")
    for gold in Verdict:
        by_gold = analysis.by_gold(gold)
        gold_n = sum(by_gold.values())
        correct = by_gold.get(Category.CORRECT, 0)
        cells = " | ".join(str(by_gold.get(category, 0)) for category in MISS_CATEGORIES)
        lines.append(f"| {gold.value} | {gold_n} | {correct} | {cells} |")
    lines.append("")

    # 3) A few representative misses per category, for the paper's qualitative read.
    if examples:
        for category in MISS_CATEGORIES:
            picked = analysis.examples(category, examples)
            if not picked:
                continue
            lines.append(f"_Example {category.value} claims:_")
            for diag in picked:
                lines.append(f"- ({diag.gold.value} → {diag.predicted.value}) {diag.claim}")
            lines.append("")

    if analysis.missing:
        lines.append(
            f"> Note: {len(analysis.missing)} sampled item(s) had no matching trace "
            f"and were excluded: {', '.join(analysis.missing)}."
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _run(args: argparse.Namespace) -> None:
    items = load_scifact_claims(args.claims)
    if args.sample is not None:
        items = stratified_sample(items, args.sample, seed=args.seed)
    traces = read_traces(args.traces)
    analysis = diagnose(items, traces)
    print(render_markdown(analysis, examples=args.examples))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aletheia.evaluation.error_analysis", description=__doc__)
    parser.add_argument("--claims", required=True, help="path to the SciFact claims JSONL file")
    parser.add_argument("--traces", required=True, help="path to the run's traces JSONL file")
    parser.add_argument(
        "--sample",
        type=int,
        help="reproduce the run's seeded, stratified sample of N claims (uses --seed)",
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="the seed the run used for --sample (default: 7)"
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=3,
        help="representative claims to quote per miss category (0 to omit; default: 3)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Console entrypoint for the offline error analysis."""
    _run(_build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
