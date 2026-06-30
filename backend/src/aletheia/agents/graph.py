"""The verification pipeline as a LangGraph state machine.

The graph is linear — (Retriever ->) Generator -> Verifier -> Aggregator -> Guardrail —
because an explicit, inspectable state machine is exactly what the evaluation harness
needs to trace and time. The Retriever node is added only when a corpus search is
configured; it slots in ahead of the generator without changing the contract callers
depend on. The Guardrail node runs last and is purely advisory: it attaches a safety
assessment and the standing disclaimer without ever editing a verdict.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from aletheia.agents.aggregator import aggregator_node
from aletheia.agents.contracts import VerificationResult
from aletheia.agents.generator import make_generator_node
from aletheia.agents.guardrails import DISCLAIMER, Advisory, SafetyAssessment, guardrail_node
from aletheia.agents.intake import make_intake_node
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


def _route_after_intake(state: PipelineState) -> str:
    """Send admitted queries down the pipeline; refused ones to the refusal node."""
    return "allow" if state["intake"].allowed else "refuse"


async def refusal_node(state: PipelineState) -> PipelineState:
    """Terminate a refused query with a clear, non-answer result and advisory.

    The Generator and Verifier never ran, so there are no verdicts to assemble; this
    produces the same ``result`` + ``safety`` shape the normal path ends with, marked
    ``refused`` so callers can surface the decline plainly rather than as a verdict.
    """
    decision = state["intake"]
    result = VerificationResult(
        query=state["query"],
        candidate_answer="",
        verdicts=[],
        refused=True,
        refusal_reason=decision.reason,
    )
    # An injection attempt is the more serious signal; an off-topic query is a caution.
    advisory = Advisory.HIGH_CAUTION if decision.category == "injection" else Advisory.CAUTION
    safety = SafetyAssessment(advisory=advisory, disclaimer=DISCLAIMER, notes=[decision.reason])
    return {"result": result, "safety": safety}


@dataclass(frozen=True, slots=True)
class StageUpdate:
    """One node's output as the graph streams: the node's name and its partial state."""

    stage: str
    update: PipelineState


class VerificationPipeline:
    """Runs a query through the grounded verification graph.

    Construct once and reuse: the graph is compiled a single time and ``run`` is safe to
    call concurrently. Pass ``retrieve`` to let the pipeline source its own evidence from
    the corpus when the caller does not supply any; without it the pipeline behaves
    exactly as in Phase 1 and a caller must provide ``evidence``.
    """

    def __init__(
        self,
        llm: LLMClient,
        *,
        retrieve: EvidenceRetriever | None = None,
        enable_scope_guard: bool = False,
    ) -> None:
        self._has_retriever = retrieve is not None

        builder = StateGraph(PipelineState)
        builder.add_node("generator", _as_node(make_generator_node(llm)))
        builder.add_node("verifier", _as_node(make_verifier_node(llm)))
        builder.add_node("aggregator", _as_node(aggregator_node))
        builder.add_node("guardrail", _as_node(guardrail_node))
        if retrieve is not None:
            builder.add_node("retriever", _as_node(make_retriever_node(retrieve)))

        # The first node of the answer path — the Retriever when configured, else straight
        # to the Generator. The scope guard, when enabled, sits in front of it.
        first = "retriever" if retrieve is not None else "generator"

        if enable_scope_guard:
            builder.add_node("intake", _as_node(make_intake_node(llm)))
            builder.add_node("refusal", _as_node(refusal_node))
            builder.add_edge(START, "intake")
            builder.add_conditional_edges(
                "intake", _route_after_intake, {"allow": first, "refuse": "refusal"}
            )
            builder.add_edge("refusal", END)
        else:
            builder.add_edge(START, first)

        if retrieve is not None:
            builder.add_edge("retriever", "generator")
        builder.add_edge("generator", "verifier")
        builder.add_edge("verifier", "aggregator")
        builder.add_edge("aggregator", "guardrail")
        builder.add_edge("guardrail", END)
        self._graph = builder.compile()

    def _initial_state(
        self, query: str, evidence: str | None, candidate_answer: str | None
    ) -> PipelineState:
        """Build (and validate) the graph's initial state for a run.

        ``evidence`` may be omitted only when the pipeline was built with a retriever,
        which will source it from the corpus; otherwise it is required.
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
        return initial

    async def ainvoke(
        self,
        query: str,
        evidence: str | None = None,
        candidate_answer: str | None = None,
    ) -> PipelineState:
        """Run the graph and return its full final state.

        Exposes the whole state (including any ``evidence_sources`` the Retriever found)
        so callers can read the grounded result and its provenance together.
        """
        initial = self._initial_state(query, evidence, candidate_answer)
        return cast(PipelineState, await self._graph.ainvoke(initial))

    async def astream(
        self,
        query: str,
        evidence: str | None = None,
        candidate_answer: str | None = None,
    ) -> AsyncIterator[StageUpdate]:
        """Stream the graph node by node, yielding each node's partial state as it lands.

        Same inputs and validation as :meth:`ainvoke`, but instead of the final state it
        yields a :class:`StageUpdate` per node (retriever, generator, verifier, aggregator,
        guardrail) so callers can surface the live agent path. Uses LangGraph's ``updates``
        stream mode, which reports one ``{node: partial_state}`` chunk per node.
        """
        initial = self._initial_state(query, evidence, candidate_answer)
        async for chunk in self._graph.astream(initial, stream_mode="updates"):
            for stage, update in chunk.items():
                # A node that writes no state surfaces as a ``None`` update in
                # ``updates`` mode — e.g. the Retriever passing through evidence the
                # caller already supplied. There is nothing to stream for it.
                if not update:
                    continue
                yield StageUpdate(stage=stage, update=cast(PipelineState, update))

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
