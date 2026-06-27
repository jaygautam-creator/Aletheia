"""The Aggregator node.

Responsibility: assemble the per-claim verdicts into the single
:class:`VerificationResult` the caller receives. In Phase 1 this is a faithful
assembly step (answer + grounded verdicts, with the summary helpers the result type
exposes). Calibrated confidence and richer disagreement analysis arrive with the
evaluation harness in later phases; the node is the seam where they will live.
"""

from __future__ import annotations

from aletheia.agents.contracts import VerificationResult
from aletheia.agents.state import PipelineState


async def aggregator_node(state: PipelineState) -> PipelineState:
    """Combine the candidate answer and verdicts into a VerificationResult."""
    result = VerificationResult(
        query=state["query"],
        candidate_answer=state["candidate_answer"],
        verdicts=state["verdicts"],
    )
    return {"result": result}
