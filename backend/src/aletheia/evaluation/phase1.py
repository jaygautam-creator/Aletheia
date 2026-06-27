"""Phase 1 comparison runner: grounded multi-agent verifier vs single-LLM baseline.

Run live with a provider key in your ``.env``::

    uv --directory backend run python -m aletheia.evaluation.phase1

Both systems judge the *same* atomic claims against the same evidence; decomposition and
retrieval are deliberately held out of this comparison (they enter in later phases) so it
isolates the effect of evidence-grounded, per-claim verification.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from aletheia.agents.contracts import Verdict
from aletheia.agents.verifier import make_verifier_node
from aletheia.evaluation.baseline import baseline_supported
from aletheia.evaluation.dataset import DatasetItem, load_mini_dataset
from aletheia.evaluation.metrics import SystemScore, format_comparison, score_system
from aletheia.llm import LLMClient, LLMConfigurationError, build_llm_client

BASELINE_NAME = "Single-LLM baseline"
GROUNDED_NAME = "Aletheia (grounded verifier)"


async def grounded_supported(llm: LLMClient, item: DatasetItem) -> list[bool]:
    """Return, per claim, whether the grounded verifier judged it supported."""
    node = make_verifier_node(llm)
    out = await node({"evidence": item.evidence, "claims": item.claim_texts})
    return [verdict.verdict is Verdict.SUPPORTED for verdict in out["verdicts"]]


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """The scored outcome of one comparison run."""

    baseline: SystemScore
    grounded: SystemScore

    def render(self) -> str:
        return format_comparison([self.baseline, self.grounded])


async def run_comparison(llm: LLMClient, items: Sequence[DatasetItem]) -> ComparisonResult:
    """Run both systems over ``items`` and score them against the gold labels."""
    gold: list[bool] = []
    baseline_pred: list[bool] = []
    grounded_pred: list[bool] = []

    for item in items:
        gold.extend(item.gold_supported)
        baseline_pred.extend(await baseline_supported(llm, item))
        grounded_pred.extend(await grounded_supported(llm, item))

    return ComparisonResult(
        baseline=score_system(BASELINE_NAME, baseline_pred, gold),
        grounded=score_system(GROUNDED_NAME, grounded_pred, gold),
    )


async def _run() -> None:
    items = load_mini_dataset()
    llm = build_llm_client()
    n_claims = sum(len(item.claims) for item in items)
    print(
        f"Phase 1 comparison · {len(items)} items / {n_claims} claims · "
        f"provider {llm.provider}:{llm.model}\n"
    )
    result = await run_comparison(llm, items)
    print(result.render())
    print()


def main() -> None:
    """Console entrypoint; exits cleanly with guidance if no provider key is set."""
    try:
        asyncio.run(_run())
    except LLMConfigurationError as exc:
        raise SystemExit(f"\nCannot run the live comparison.\n{exc}\n") from exc


if __name__ == "__main__":
    main()
