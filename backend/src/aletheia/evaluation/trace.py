"""Structured per-run traces for the evaluation harness.

Every benchmark query produces a :class:`RunTrace` — its inputs, the evidence spans
retrieved to ground it, the per-claim verdicts, the LLM calls (tokens + latency), and
the end-to-end wall-clock — written one JSON object per line. Traces make a run
auditable and are the substrate for error analysis (EVALUATION.md §5); they are a
read-only record and never feed back into the verdicts.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aletheia.agents.contracts import VerificationResult
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.llm.base import TokenUsage
from aletheia.llm.recording import CallRecord


@dataclass(frozen=True, slots=True)
class RetrievedSpan:
    """An evidence span the retriever surfaced for a query."""

    external_id: str
    title: str
    trust_tier: str
    score: float
    text: str


@dataclass(frozen=True, slots=True)
class VerdictTrace:
    """One claim's verdict, flattened for the trace record."""

    claim: str
    verdict: str
    quoted_span: str | None


@dataclass(frozen=True, slots=True)
class RunTrace:
    """The complete, auditable record of one verification run."""

    query: str
    candidate_answer: str
    latency_s: float
    evidence: list[RetrievedSpan]
    verdicts: list[VerdictTrace]
    llm_calls: list[CallRecord]

    @property
    def total_usage(self) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=sum(call.prompt_tokens for call in self.llm_calls),
            completion_tokens=sum(call.completion_tokens for call in self.llm_calls),
        )


def build_run_trace(
    result: VerificationResult,
    sources: Sequence[RetrievedEvidence],
    calls: Sequence[CallRecord],
    *,
    latency_s: float,
) -> RunTrace:
    """Assemble a :class:`RunTrace` from a finished run's result, sources, and calls."""
    return RunTrace(
        query=result.query,
        candidate_answer=result.candidate_answer,
        latency_s=latency_s,
        evidence=[
            RetrievedSpan(
                external_id=source.external_id,
                title=source.title,
                trust_tier=str(source.trust_tier),
                score=source.score,
                text=source.text,
            )
            for source in sources
        ],
        verdicts=[
            VerdictTrace(claim=v.claim, verdict=str(v.verdict), quoted_span=v.quoted_span)
            for v in result.verdicts
        ],
        llm_calls=list(calls),
    )


def write_traces(path: str | Path, traces: Iterable[RunTrace]) -> None:
    """Write traces as JSONL — one trace per line — overwriting ``path``."""
    content = "\n".join(json.dumps(asdict(trace)) for trace in traces)
    Path(path).write_text(content + "\n" if content else "", encoding="utf-8")


def read_traces(path: str | Path) -> list[RunTrace]:
    """Read traces back from a JSONL file written by :func:`write_traces`."""
    text = Path(path).read_text(encoding="utf-8")
    return [_trace_from_dict(json.loads(line)) for line in text.splitlines() if line.strip()]


def _trace_from_dict(data: dict[str, Any]) -> RunTrace:
    return RunTrace(
        query=data["query"],
        candidate_answer=data["candidate_answer"],
        latency_s=data["latency_s"],
        evidence=[RetrievedSpan(**span) for span in data["evidence"]],
        verdicts=[VerdictTrace(**verdict) for verdict in data["verdicts"]],
        llm_calls=[CallRecord(**call) for call in data["llm_calls"]],
    )
