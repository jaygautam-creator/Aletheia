"""The verification pipeline as a LangGraph state machine.

The graph is linear — (Retriever ->) Generator -> Verifier -> Aggregator — because an
explicit, inspectable state machine is exactly what the evaluation harness needs to
trace and time. The Retriever node is added only when a corpus search is configured; it
slots in ahead of the generator without changing the contract callers depend on. The
guardrail node joins the same graph in a later phase.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from aletheia.agents.aggregator import aggregator_node
from aletheia.agents.contracts import VerificationResult
from aletheia.agents.generator import make_generator_node
from aletheia.agents.retriever import EvidenceRetriever, make_retriever_node
from aletheia.agents.state import PipelineState
from aletheia.agents.verifier import make_verifier_node
from aletheia.llm import LLMClient

_PipelineNode = Callable[[PipelineState], Awaitable[PipelineState]]


def _as_node(node: _PipelineNode) -> Any:
    """Adapt a typed pipeline node to LangGraph's ``add_node`` signature.

    LangGraph types nodes through a ``Protocol`` typevar that mypy cannot infer from a
    passed callable, so a precise annotation is impossible at the call site. The cast is
    confined to this one boundary; every node remains fully typed as ``_PipelineNode``.
    """
    return cast(Any, node)


class VerificationPipeline:
    """Runs a query through the grounded verification graph.

    Construct once and reuse: the graph is compiled a single time and ``run`` is safe to
    call concurrently. Pass ``retrieve`` to let the pipeline source its own evidence from
    the corpus when the caller does not supply any; without it the pipeline behaves
    exactly as in Phase 1 and a caller must provide ``evidence``.
    """

    def __init__(self, llm: LLMClient, *, retrieve: EvidenceRetriever | None = None) -> None:
        self._has_retriever = retrieve is not None

        builder = StateGraph(PipelineState)
        builder.add_node("generator", _as_node(make_generator_node(llm)))
        builder.add_node("verifier", _as_node(make_verifier_node(llm)))
        builder.add_node("aggregator", _as_node(aggregator_node))
        if retrieve is not None:
            builder.add_node("retriever", _as_node(make_retriever_node(retrieve)))
            builder.add_edge(START, "retriever")
            builder.add_edge("retriever", "generator")
        else:
            builder.add_edge(START, "generator")
        builder.add_edge("generator", "verifier")
        builder.add_edge("verifier", "aggregator")
        builder.add_edge("aggregator", END)
        self._graph = builder.compile()

    async def ainvoke(
        self,
        query: str,
        evidence: str | None = None,
        candidate_answer: str | None = None,
    ) -> PipelineState:
        """Run the graph and return its full final state.

        ``evidence`` may be omitted only when the pipeline was built with a retriever,
        which will source it from the corpus; otherwise it is required. Exposes the whole
        state (including any ``evidence_sources`` the Retriever found) so callers can read
        the grounded result and its provenance together.
        """
        if evidence is None and not self._has_retriever:
            raise ValueError(
                "evidence is required: this pipeline has no retriever to source it from."
            )

        initial: PipelineState = {"query": query}
        if evidence is not None:
            initial["evidence"] = evidence
        if candidate_answer is not None:
            initial["candidate_answer"] = candidate_answer

        return cast(PipelineState, await self._graph.ainvoke(initial))

    async def run(
        self,
        query: str,
        evidence: str | None = None,
        candidate_answer: str | None = None,
    ) -> VerificationResult:
        """Verify ``query`` against ``evidence`` and return the assembled result.

        If ``candidate_answer`` is given, that answer is the one decomposed and checked;
        otherwise the Generator produces one. ``evidence`` is retrieved from the corpus
        when omitted (and a retriever is configured).
        """
        final_state = await self.ainvoke(query, evidence, candidate_answer)
        return final_state["result"]
