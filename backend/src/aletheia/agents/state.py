"""The state object that flows through the verification graph.

LangGraph nodes read and write a shared, typed mapping. Keeping it a plain
``TypedDict`` (rather than importing LangGraph here) keeps the contract legible
and dependency-free: each node fills in the keys it is responsible for, so the
state grows as it moves Generator -> Verifier -> Aggregator.
"""

from __future__ import annotations

from typing import TypedDict

from aletheia.agents.contracts import ClaimVerdict, VerificationResult


class PipelineState(TypedDict, total=False):
    """Shared state for one run of the verification pipeline.

    ``total=False`` because keys are populated progressively as the run advances;
    a node may assume only that the keys written by upstream nodes are present.
    """

    # Inputs.
    query: str
    """The user's question."""

    evidence: str
    """The source passage the Verifier must ground its verdicts in.

    In Phase 1 this is supplied with the dataset item. From Phase 2 it is produced
    by the Retriever, with no change to the downstream contract.
    """

    # Generator output.
    candidate_answer: str
    """The candidate answer produced by the Generator."""

    claims: list[str]
    """Atomic, independently checkable claims extracted from the answer."""

    # Verifier output.
    verdicts: list[ClaimVerdict]
    """One grounded verdict per claim."""

    # Aggregator output.
    result: VerificationResult
    """The assembled, returnable result for this run."""
