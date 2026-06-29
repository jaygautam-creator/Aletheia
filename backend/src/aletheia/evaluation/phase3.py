"""Phase 3 benchmark runner: grounded multi-agent verifier vs single-LLM baseline.

Both systems judge the *same* SciFact claim against the *same* evidence retrieved from
the frozen corpus; they differ only in the verification architecture (EVALUATION.md §5),
so the gap between them isolates the contribution of evidence-grounded verification:

* **Aletheia (grounded verifier)** — the Verifier judges the claim and may affirm it only
  by quoting a verbatim span, with the verdict downgraded to ``Unverifiable`` otherwise.
* **Single-LLM baseline** — one holistic call labels the claim against the evidence, with
  no span discipline.

Decomposition (the Generator) is held out: SciFact claims are already atomic, so running
it would only blur the claim↔gold-label alignment the score depends on. Retrieval is
shared and held fixed, so the per-system latency and cost measure each system's own work.

Run live with a provider key, a running database, and the SciFact corpus ingested::

    uv --directory backend run python -m aletheia.evaluation.phase3 \\
        --claims data/scifact/claims_dev.jsonl --limit 100 --traces runs/scifact.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter

from aletheia.agents import EvidenceRetriever
from aletheia.agents.contracts import ClaimVerdict, Verdict, VerificationResult
from aletheia.agents.verifier import make_verifier_node
from aletheia.corpus.retrieval import Retriever, format_evidence
from aletheia.db.session import get_sessionmaker
from aletheia.embeddings import EmbeddingConfigurationError, build_embedder
from aletheia.evaluation.benchmark import BenchmarkItem, load_scifact_claims
from aletheia.evaluation.metrics import (
    CostStats,
    LatencyStats,
    VerdictScore,
    cost_from_usages,
    latency_percentiles,
    score_verdicts,
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

_BASELINE_SYSTEM = (
    "You judge whether evidence supports a single scientific claim. Reply with JSON only: "
    '{"verdict": "Supported" | "Contradicted" | "Unverifiable"}. Use "Supported" if the '
    'evidence supports the claim, "Contradicted" if it refutes the claim, and '
    '"Unverifiable" if the evidence is insufficient. Judge only against the evidence; do '
    "not use outside knowledge."
)


async def grounded_claim_verdict(llm: LLMClient, claim: str, evidence: str) -> ClaimVerdict:
    """The grounded system's verdict: the Verifier, which must quote a span to affirm."""
    node = make_verifier_node(llm)
    out = await node({"evidence": evidence, "claims": [claim]})
    return out["verdicts"][0]


def _parse_verdict(data: object) -> Verdict:
    if not isinstance(data, dict):
        raise LLMError(f"Baseline expected a JSON object, got {type(data).__name__}.")
    raw = data.get("verdict")
    if not isinstance(raw, str):
        raise LLMError("Baseline response is missing a string 'verdict'.")
    normalised = raw.strip().lower()
    for verdict in Verdict:
        if verdict.value.lower() == normalised:
            return verdict
    raise LLMError(f"Baseline returned an unknown verdict: {raw!r}.")


async def baseline_claim_verdict(llm: LLMClient, claim: str, evidence: str) -> Verdict:
    """The single-LLM baseline's verdict: one holistic call, no span discipline."""
    user = f"EVIDENCE:\n{evidence}\n\nCLAIM:\n{claim}"
    data = await llm.generate_json([Message.system(_BASELINE_SYSTEM), Message.user(user)])
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
    """The scored outcome of one benchmark run, plus the grounded system's traces."""

    n_items: int
    grounded: SystemReport
    baseline: SystemReport
    traces: list[RunTrace]

    def render(self) -> str:
        header = (
            f"{'System':<30}  {'Accuracy':>9}  {'Catch':>7}  {'FalseAgree':>10}  "
            f"{'Latency p50/p95/p99 (s)':>26}  {'Tokens/q':>9}"
        )
        lines = [f"SciFact benchmark · {self.n_items} claims\n", header, "-" * len(header)]
        for report in (self.baseline, self.grounded):
            latency = (
                f"{report.latency.p50:.3f} / {report.latency.p95:.3f} / {report.latency.p99:.3f}"
            )
            lines.append(
                f"{report.name:<30}  "
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
) -> BenchmarkReport:
    """Run both systems over ``items``, grounding each claim in retrieved evidence."""
    grounded_llm = RecordingLLMClient(llm)
    baseline_llm = RecordingLLMClient(llm)

    gold: list[Verdict] = []
    grounded_pred: list[Verdict] = []
    baseline_pred: list[Verdict] = []
    grounded_latencies: list[float] = []
    baseline_latencies: list[float] = []
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
    )


async def _run(args: argparse.Namespace) -> None:
    items = load_scifact_claims(args.claims)
    if args.limit is not None:
        items = items[: args.limit]
    if not items:
        raise SystemExit("no claims to run")

    embedder = build_embedder()
    llm = build_llm_client()
    print(
        f"Phase 3 SciFact benchmark · {len(items)} claims · provider {llm.provider}:{llm.model}\n"
    )
    async with get_sessionmaker()() as session:
        retriever = Retriever(session, embedder=embedder)
        report = await run_benchmark(items, retrieve=retriever.search, llm=llm)

    print(report.render())
    if args.traces:
        write_traces(args.traces, report.traces)
        print(f"\nwrote {len(report.traces)} traces → {args.traces}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aletheia.evaluation.phase3", description=__doc__)
    parser.add_argument("--claims", required=True, help="path to a SciFact claims JSONL file")
    parser.add_argument("--limit", type=int, help="run at most this many claims")
    parser.add_argument("--traces", help="write per-run traces to this JSONL path")
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
