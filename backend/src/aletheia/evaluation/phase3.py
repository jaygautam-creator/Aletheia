"""Phase 3 benchmark runner: grounded multi-agent verifier vs single-LLM baseline.

Both systems judge the *same* SciFact claim against the *same* evidence retrieved from
the frozen corpus; they differ only in the verification architecture (EVALUATION.md §5),
so the gap between them isolates the contribution of evidence-grounded verification:

* **Aletheia (grounded verifier)** — the Verifier judges the claim and may affirm it only
  by quoting a verbatim span, with the verdict downgraded to ``Unverifiable`` otherwise.
* **Single-LLM baseline** — one holistic call labels the claim against the evidence, with
  no span discipline.
* **Ungrounded multi-agent (``--ablation``, H2)** — the *same* per-claim critic as the
  grounded arm with the span discipline removed: verdicts are opinions, never checked
  against the evidence text. The grounded-vs-ungrounded gap isolates exactly what
  quoted-span grounding contributes, holding the multi-agent structure fixed.

Decomposition (the Generator) is held out: SciFact claims are already atomic, so running
it would only blur the claim↔gold-label alignment the score depends on. Retrieval is
shared and held fixed, so the per-system latency and cost measure each system's own work.

Run live with a provider key, a running database, and the SciFact corpus ingested.
``--sample`` draws a seeded, gold-label-stratified subset (the representative choice for
headline runs; ``--limit`` head-slices for smoke tests), and corpus coverage is checked
and printed before the first call::

    uv --directory backend run python -m aletheia.evaluation.phase3 \\
        --claims data/scifact/claims_dev.jsonl --sample 100 --seed 7 \\
        --traces runs/scifact.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.agents import EvidenceRetriever
from aletheia.agents.contracts import ClaimVerdict, Verdict, VerificationResult
from aletheia.agents.prompts import verify_ungrounded_messages
from aletheia.agents.verifier import make_verifier_node
from aletheia.corpus.models import Source
from aletheia.corpus.retrieval import Retriever, format_evidence
from aletheia.db.session import get_sessionmaker
from aletheia.embeddings import EmbeddingConfigurationError, build_embedder
from aletheia.evaluation.benchmark import (
    BenchmarkItem,
    Coverage,
    coverage_against,
    load_scifact_claims,
    stratified_sample,
)
from aletheia.evaluation.metrics import (
    CostStats,
    LatencyStats,
    VerdictScore,
    cost_from_usages,
    latency_percentiles,
    score_verdicts,
)
from aletheia.evaluation.report import (
    aggregate_reports,
    render_markdown,
    render_significance,
    update_evaluation_md,
    write_frontend_json,
)
from aletheia.evaluation.trace import RunTrace, build_run_trace, write_traces
from aletheia.llm import (
    LLMClient,
    LLMConfigurationError,
    LLMError,
    Message,
    RecordingLLMClient,
    build_llm_client,
)

GROUNDED_NAME = "Aletheia (grounded verifier)"
BASELINE_NAME = "Single-LLM baseline"
UNGROUNDED_NAME = "Multi-agent, ungrounded (ablation)"

#: Below this corpus-coverage fraction a run's numbers are suspect (claims whose cited
#: abstracts are missing can only come back Unverifiable), so the runner warns loudly.
COVERAGE_FLOOR = 0.95

_BASELINE_SYSTEM = (
    "You judge whether evidence supports a single scientific claim. Reply with JSON only: "
    '{"verdict": "Supported" | "Contradicted" | "Unverifiable"}. Use "Supported" if the '
    'evidence supports the claim, "Contradicted" if it refutes the claim, and '
    '"Unverifiable" if the evidence is insufficient. Judge only against the evidence; do '
    "not use outside knowledge."
)


async def corpus_coverage(
    session: AsyncSession, items: Sequence[BenchmarkItem], *, connector: str = "scifact"
) -> Coverage:
    """Check the items' cited documents against what the corpus has actually ingested.

    One query for the connector's ingested ``external_id``s, then the pure set logic of
    :func:`coverage_against` — run this before a benchmark so missing abstracts surface
    as a loud warning up front, not as a mysteriously deflated score afterwards.
    """
    query = select(Source.external_id).where(Source.connector == connector)
    ingested = await session.execute(query)
    return coverage_against(items, set(ingested.scalars()))


async def grounded_claim_verdict(llm: LLMClient, claim: str, evidence: str) -> ClaimVerdict:
    """The grounded system's verdict: the Verifier, which must quote a span to affirm."""
    node = make_verifier_node(llm)
    out = await node({"evidence": evidence, "claims": [claim]})
    return out["verdicts"][0]


def _parse_verdict(data: object) -> Verdict:
    """Parse a bare three-way verdict reply (shared by the baseline and ablation arms)."""
    if not isinstance(data, dict):
        raise LLMError(f"Expected a JSON verdict object, got {type(data).__name__}.")
    raw = data.get("verdict")
    if not isinstance(raw, str):
        raise LLMError("Verdict reply is missing a string 'verdict'.")
    normalised = raw.strip().lower()
    for verdict in Verdict:
        if verdict.value.lower() == normalised:
            return verdict
    raise LLMError(f"Unknown verdict: {raw!r}.")


async def baseline_claim_verdict(llm: LLMClient, claim: str, evidence: str) -> Verdict:
    """The single-LLM baseline's verdict: one holistic call, no span discipline."""
    user = f"EVIDENCE:\n{evidence}\n\nCLAIM:\n{claim}"
    data = await llm.generate_json([Message.system(_BASELINE_SYSTEM), Message.user(user)])
    return _parse_verdict(data)


async def ungrounded_claim_verdict(llm: LLMClient, claim: str, evidence: str) -> Verdict:
    """The H2 ablation arm's verdict: the same per-claim critic, span discipline removed.

    The prompt mirrors the grounded Verifier's word for word except for the quoted-span
    requirement (see :data:`aletheia.agents.prompts._VERIFY_UNGROUNDED`'s fairness
    contract), and the reply is taken as-is — no span, no ``grounded_against`` check —
    so the grounded-vs-ungrounded gap measures grounding alone.
    """
    data = await llm.generate_json(verify_ungrounded_messages(claim, evidence))
    return _parse_verdict(data)


@dataclass(frozen=True, slots=True)
class SystemReport:
    """One system's scored result over the benchmark."""

    name: str
    score: VerdictScore
    latency: LatencyStats
    cost: CostStats


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """The scored outcome of one benchmark run, plus the grounded system's traces.

    ``ungrounded`` is present only when the run included the H2 ablation arm
    (``--ablation``); the two headline systems are always present. Reporting order is
    everywhere baseline → ungrounded → grounded (ascending discipline).

    ``gold`` and the ``*_pred`` lists are the run's raw per-claim verdicts, index-aligned
    with each other (one entry per benchmark item, in run order). They are the material
    for paired significance testing and error analysis; the ``SystemReport`` scores above
    are derived from them.
    """

    n_items: int
    grounded: SystemReport
    baseline: SystemReport
    traces: list[RunTrace]
    ungrounded: SystemReport | None = None
    gold: list[Verdict] = field(default_factory=list)
    baseline_pred: list[Verdict] = field(default_factory=list)
    grounded_pred: list[Verdict] = field(default_factory=list)
    ungrounded_pred: list[Verdict] | None = None

    def _systems(self) -> tuple[SystemReport, ...]:
        """The systems in reporting order, including the ablation arm only when run."""
        if self.ungrounded is None:
            return (self.baseline, self.grounded)
        return (self.baseline, self.ungrounded, self.grounded)

    def render(self) -> str:
        header = (
            f"{'System':<33}  {'Accuracy':>9}  {'Catch':>7}  {'FalseAgree':>10}  "
            f"{'Latency p50/p95/p99 (s)':>26}  {'Tokens/q':>9}"
        )
        lines = [f"SciFact benchmark · {self.n_items} claims\n", header, "-" * len(header)]
        for report in self._systems():
            latency = (
                f"{report.latency.p50:.3f} / {report.latency.p95:.3f} / {report.latency.p99:.3f}"
            )
            lines.append(
                f"{report.name:<33}  "
                f"{report.score.accuracy * 100:>8.1f}%  "
                f"{report.score.catch_rate * 100:>6.1f}%  "
                f"{report.score.false_agreement_rate * 100:>9.1f}%  "
                f"{latency:>26}  "
                f"{report.cost.tokens_per_query:>9.1f}"
            )
        return "\n".join(lines)


async def run_benchmark(
    items: Sequence[BenchmarkItem],
    *,
    retrieve: EvidenceRetriever,
    llm: LLMClient,
    ablation: bool = False,
) -> BenchmarkReport:
    """Run the systems over ``items``, grounding each claim in retrieved evidence.

    Always runs the grounded verifier and the single-LLM baseline; ``ablation`` adds
    the ungrounded multi-agent arm (H2). All arms judge the same claim against the same
    retrieved evidence with the same model, so every gap is architectural.
    """
    grounded_llm = RecordingLLMClient(llm)
    baseline_llm = RecordingLLMClient(llm)
    ungrounded_llm = RecordingLLMClient(llm)

    gold: list[Verdict] = []
    grounded_pred: list[Verdict] = []
    baseline_pred: list[Verdict] = []
    ungrounded_pred: list[Verdict] = []
    grounded_latencies: list[float] = []
    baseline_latencies: list[float] = []
    ungrounded_latencies: list[float] = []
    traces: list[RunTrace] = []

    for item in items:
        sources = list(await retrieve(item.claim))
        evidence = format_evidence(sources)
        gold.append(item.gold)

        before = len(grounded_llm.records)
        start = perf_counter()
        verdict = await grounded_claim_verdict(grounded_llm, item.claim, evidence)
        grounded_latencies.append(perf_counter() - start)
        grounded_pred.append(verdict.verdict)
        traces.append(
            build_run_trace(
                VerificationResult(
                    query=item.claim, candidate_answer=item.claim, verdicts=[verdict]
                ),
                sources,
                grounded_llm.records[before:],
                latency_s=grounded_latencies[-1],
            )
        )

        start = perf_counter()
        baseline_pred.append(await baseline_claim_verdict(baseline_llm, item.claim, evidence))
        baseline_latencies.append(perf_counter() - start)

        if ablation:
            start = perf_counter()
            ungrounded_pred.append(
                await ungrounded_claim_verdict(ungrounded_llm, item.claim, evidence)
            )
            ungrounded_latencies.append(perf_counter() - start)

    ungrounded: SystemReport | None = None
    if ablation:
        ungrounded = SystemReport(
            name=UNGROUNDED_NAME,
            score=score_verdicts(UNGROUNDED_NAME, ungrounded_pred, gold),
            latency=latency_percentiles(ungrounded_latencies),
            cost=cost_from_usages(ungrounded_llm.usages),
        )

    return BenchmarkReport(
        n_items=len(items),
        grounded=SystemReport(
            name=GROUNDED_NAME,
            score=score_verdicts(GROUNDED_NAME, grounded_pred, gold),
            latency=latency_percentiles(grounded_latencies),
            cost=cost_from_usages(grounded_llm.usages),
        ),
        baseline=SystemReport(
            name=BASELINE_NAME,
            score=score_verdicts(BASELINE_NAME, baseline_pred, gold),
            latency=latency_percentiles(baseline_latencies),
            cost=cost_from_usages(baseline_llm.usages),
        ),
        traces=traces,
        ungrounded=ungrounded,
        gold=gold,
        baseline_pred=baseline_pred,
        grounded_pred=grounded_pred,
        ungrounded_pred=ungrounded_pred if ablation else None,
    )


def _label_distribution(items: Sequence[BenchmarkItem]) -> str:
    """The sample's gold-label mix, e.g. ``Supported 83 · Contradicted 41 · Unverifiable 26``."""
    counts = Counter(item.gold for item in items)
    return " · ".join(f"{verdict.value} {counts.get(verdict, 0)}" for verdict in Verdict)


async def _run(args: argparse.Namespace) -> None:
    items = load_scifact_claims(args.claims)
    if args.limit is not None:
        items = items[: args.limit]
    elif args.sample is not None:
        items = stratified_sample(items, args.sample, seed=args.seed)
    if not items:
        raise SystemExit("no claims to run")

    embedder = build_embedder()
    llm = build_llm_client()
    arms = "3 arms (with ungrounded ablation)" if args.ablation else "2 arms"
    print(
        f"Phase 3 SciFact benchmark · {len(items)} claims · {args.repeats} repeat(s) · "
        f"{arms} · provider {llm.provider}:{llm.model}"
    )
    print(f"gold labels: {_label_distribution(items)}\n")
    async with get_sessionmaker()() as session:
        coverage = await corpus_coverage(session, items)
        print(
            f"corpus coverage: {coverage.n_covered}/{coverage.n_items} claims have every "
            f"cited abstract ingested ({coverage.fraction * 100:.1f}%)"
        )
        if coverage.fraction < COVERAGE_FLOOR:
            print(
                f"WARNING: coverage is below {COVERAGE_FLOOR * 100:.0f}% — claims with "
                "missing abstracts can only come back Unverifiable, so these numbers "
                "will understate every system. Ingest the SciFact corpus first."
            )
        retriever = Retriever(session, embedder=embedder)
        reports = [
            await run_benchmark(items, retrieve=retriever.search, llm=llm, ablation=args.ablation)
            for _ in range(args.repeats)
        ]

    aggregated = aggregate_reports(reports)
    markdown = render_markdown(
        aggregated,
        model=f"{llm.provider}:{llm.model}",
        seed=args.seed,
        coverage=coverage.fraction,
        run_date=date.today().isoformat(),
    )
    significance = render_significance(reports[0])
    if significance is not None:
        markdown = f"{markdown}\n\n{significance}"
    print(markdown)
    if args.traces:
        write_traces(args.traces, reports[0].traces)
        print(f"\nwrote {len(reports[0].traces)} traces → {args.traces}")
    if args.write_eval:
        update_evaluation_md(args.write_eval, markdown)
        print(f"updated {args.write_eval}")
    if args.write_frontend:
        write_frontend_json(
            args.write_frontend,
            aggregated,
            model=f"{llm.provider}:{llm.model}",
            seed=args.seed,
        )
        print(f"wrote frontend benchmark record → {args.write_frontend}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aletheia.evaluation.phase3", description=__doc__)
    parser.add_argument("--claims", required=True, help="path to a SciFact claims JSONL file")
    subset = parser.add_mutually_exclusive_group()
    subset.add_argument(
        "--limit", type=int, help="head-slice: run the first N claims (smoke runs only)"
    )
    subset.add_argument(
        "--sample",
        type=int,
        help=(
            "draw a seeded, gold-label-stratified random sample of N claims — the "
            "representative subset for headline runs (uses --seed)"
        ),
    )
    parser.add_argument(
        "--repeats", type=int, default=1, help="seeded repeats to average for mean ± std"
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help=(
            "also run the ungrounded multi-agent arm (the same per-claim critic with the "
            "span discipline removed) — the H2 ablation; costs one extra call per claim"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="drives --sample's draw and is recorded with the run for reproducibility",
    )
    parser.add_argument("--traces", help="write per-run traces (of the first repeat) to this path")
    parser.add_argument(
        "--write-eval", help="rewrite the §6.2 table between the PHASE3 markers of this file"
    )
    parser.add_argument(
        "--write-frontend",
        help="write the frontend benchmark record (JSON) the landing chart and /benchmark read",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Console entrypoint; exits cleanly with guidance if the run cannot be configured."""
    args = _build_parser().parse_args(argv)
    try:
        asyncio.run(_run(args))
    except (LLMConfigurationError, EmbeddingConfigurationError) as exc:
        raise SystemExit(f"\nCannot run the benchmark.\n{exc}\n") from exc


if __name__ == "__main__":
    main()
