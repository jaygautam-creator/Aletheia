"""Phase 1 evaluation: the first measurable comparison.

This subpackage is the seed of the project's centerpiece. It holds a small curated
dataset with deliberately planted unsupported claims, a single-LLM baseline, and the
metrics that put the grounded multi-agent verifier next to that baseline on the same
claims. The full benchmark harness over public datasets arrives in Phase 3 and builds
on these same metric definitions.
"""

from aletheia.evaluation.benchmark import BenchmarkItem, load_scifact_claims, parse_scifact_claim
from aletheia.evaluation.dataset import DatasetItem, GoldClaim, load_mini_dataset
from aletheia.evaluation.metrics import SystemScore, format_comparison, score_system

__all__ = [
    "BenchmarkItem",
    "DatasetItem",
    "GoldClaim",
    "SystemScore",
    "format_comparison",
    "load_mini_dataset",
    "load_scifact_claims",
    "parse_scifact_claim",
    "score_system",
]
