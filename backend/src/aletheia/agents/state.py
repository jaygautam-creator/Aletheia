"""The state object that flows through the verification graph.

LangGraph nodes read and write a shared, typed mapping. Keeping it a plain
``TypedDict`` (rather than importing LangGraph here) keeps the contract legible
and dependency-free: each node fills in the keys it is responsible for, so the
state grows as it moves Generator -> Verifier -> Aggregator.
"""

from __future__ import annotations

from typing import TypedDict

from aletheia.agents.contracts import ClaimVerdict, VerificationResult
from aletheia.agents.guardrails import SafetyAssessment
from aletheia.corpus.retrieval import RetrievedEvidence


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

    In Phase 1 this is supplied with the dataset item. From Phase 2 the Retriever node
    produces it from the corpus when it is not supplied, with no change to the
    downstream contract.
    """

    evidence_sources: list[RetrievedEvidence]
    """The trust-tiered corpus chunks the Retriever node grounded ``evidence`` in.

    Populated only when the Retriever node runs (i.e. the caller did not supply
    ``evidence``); it is the structured provenance behind the formatted ``evidence``
    string, surfaced as citations. Additive — the verdict contract is unaffected.
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

    # Guardrail output.
    safety: SafetyAssessment
    """The guardrail's advisory over the result, plus the standing disclaimer.

    Set by the guardrail node at the end of the graph. It is purely additive — the
    guardrail never edits a verdict or the answer, so the verdict contract is unchanged.
    """
