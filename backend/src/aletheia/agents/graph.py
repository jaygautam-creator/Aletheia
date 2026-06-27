"""The verification pipeline as a LangGraph state machine.

The graph is intentionally linear in Phase 1 — Generator -> Verifier -> Aggregator —
because an explicit, inspectable state machine is exactly what the evaluation harness
needs to trace and time. Retrieval and guardrail nodes slot into this same graph in
later phases without changing the contract callers depend on.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from aletheia.agents.aggregator import aggregator_node
from aletheia.agents.contracts import VerificationResult
from aletheia.agents.generator import make_generator_node
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

    Construct once with an :class:`~aletheia.llm.base.LLMClient` and reuse: the graph is
    compiled a single time. ``run`` is safe to call concurrently.
    """

    def __init__(self, llm: LLMClient) -> None:
        builder = StateGraph(PipelineState)
        builder.add_node("generator", _as_node(make_generator_node(llm)))
        builder.add_node("verifier", _as_node(make_verifier_node(llm)))
        builder.add_node("aggregator", _as_node(aggregator_node))
        builder.add_edge(START, "generator")
        builder.add_edge("generator", "verifier")
        builder.add_edge("verifier", "aggregator")
        builder.add_edge("aggregator", END)
        self._graph = builder.compile()

    async def run(
        self,
        query: str,
        evidence: str,
        candidate_answer: str | None = None,
    ) -> VerificationResult:
        """Verify ``query`` against ``evidence``.

        If ``candidate_answer`` is given, that answer is the one decomposed and checked;
        otherwise the Generator produces one. Returns the assembled grounded result.
        """
        initial: PipelineState = {"query": query, "evidence": evidence}
        if candidate_answer is not None:
            initial["candidate_answer"] = candidate_answer

        final_state = await self._graph.ainvoke(initial)
        return cast(VerificationResult, final_state["result"])
