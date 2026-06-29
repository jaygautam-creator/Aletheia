"""Phase 1 evaluation: the first measurable comparison.

This subpackage is the seed of the project's centerpiece. It holds a small curated
dataset with deliberately planted unsupported claims, a single-LLM baseline, and the
metrics that put the grounded multi-agent verifier next to that baseline on the same
claims. The full benchmark harness over public datasets arrives in Phase 3 and builds
on these same metric definitions.
"""

from aletheia.evaluation.benchmark import BenchmarkItem, load_scifact_claims, parse_scifact_claim
from aletheia.evaluation.dataset import DatasetItem, GoldClaim, load_mini_dataset
from aletheia.evaluation.metrics import (
    CostStats,
    LatencyStats,
    MeanStd,
    SystemScore,
    VerdictScore,
    cost_from_usages,
    format_comparison,
    latency_percentiles,
    score_system,
    score_verdicts,
    summarize,
)
from aletheia.evaluation.trace import (
    RetrievedSpan,
    RunTrace,
    VerdictTrace,
    build_run_trace,
    read_traces,
    write_traces,
)
from aletheia.llm.base import TokenUsage

__all__ = [
    "BenchmarkItem",
    "CostStats",
    "DatasetItem",
    "GoldClaim",
    "LatencyStats",
    "MeanStd",
    "RetrievedSpan",
    "RunTrace",
    "SystemScore",
    "TokenUsage",
    "VerdictScore",
    "VerdictTrace",
    "build_run_trace",
    "cost_from_usages",
    "format_comparison",
    "latency_percentiles",
    "load_mini_dataset",
    "load_scifact_claims",
    "parse_scifact_claim",
    "read_traces",
    "score_system",
    "score_verdicts",
    "summarize",
    "write_traces",
]
