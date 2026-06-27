"""Agent pipeline: contracts, state, nodes, and the LangGraph wiring.

This package holds Aletheia's verification logic. Phase 1 implements a minimal
Generator + grounded Verifier; later phases add retrieval, guardrails, and the
aggregator surface described in the architecture document.
"""

from aletheia.agents.contracts import (
    GROUNDED_VERDICTS,
    ClaimVerdict,
    Verdict,
    VerificationResult,
)
from aletheia.agents.graph import VerificationPipeline
from aletheia.agents.state import PipelineState

__all__ = [
    "GROUNDED_VERDICTS",
    "ClaimVerdict",
    "PipelineState",
    "Verdict",
    "VerificationPipeline",
    "VerificationResult",
]
