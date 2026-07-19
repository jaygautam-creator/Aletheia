"""The Retriever node — where evidence enters the pipeline for the Verifier to ground in.

In Phase 1 the evidence was supplied with each request. From Phase 2 this node fills it
from the curated corpus: it searches for the query and formats the trust-tiered hits
into the single evidence block the Verifier checks against. The node is deliberately a
*pass-through when evidence is already present*, so the controlled evaluation (which
supplies its own evidence) and any caller that brings its own text are untouched — the
downstream contract does not change, retrieval is purely additive.

From ADR-0012 the node can hold a *second* retriever — the live Wikipedia fallback — and
picks between the two per request from the Intake guard's ruling: ``category="ok"`` (a
medical topic) searches the curated corpus as always, ``category="out_of_scope"`` (a
general topic, no longer refused) searches Wikipedia live instead. Never both; never
without an Intake ruling on hand when a fallback is configured.

The node depends on injected :data:`EvidenceRetriever` callables rather than a database
session so the graph stays unit-testable offline; the production retrievers (pgvector +
keyword search over the live corpus; the live Wikipedia fetch) are wired in at the API
edge.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from aletheia.agents.state import PipelineState
from aletheia.corpus.retrieval import RetrievedEvidence, format_evidence

#: An async search over the corpus: a query in, ranked trust-tiered evidence out. The
#: graph depends only on this shape, so the database-backed Retriever can be swapped for
#: a scripted one in tests.
EvidenceRetriever = Callable[[str], Awaitable[Sequence[RetrievedEvidence]]]

RetrieverNode = Callable[[PipelineState], Awaitable[PipelineState]]


def make_retriever_node(
    retrieve: EvidenceRetriever, *, general_retrieve: EvidenceRetriever | None = None
) -> RetrieverNode:
    """Build the Retriever node bound to the corpus search (and optional live fallback).

    ``general_retrieve``, when given, is used instead of ``retrieve`` whenever the Intake
    guard classified the query ``out_of_scope`` for the medical corpus (ADR-0012); with
    no Intake ruling on hand (the scope guard disabled) or no ``general_retrieve``
    configured, every query falls through to ``retrieve`` exactly as before ADR-0012.
    """

    async def retriever(state: PipelineState) -> PipelineState:
        # Respect evidence the caller already supplied (e.g. the evaluation harness):
        # only the empty/absent case triggers a search.
        if state.get("evidence") is not None:
            return {}

        intake = state.get("intake")
        is_general_topic = intake is not None and intake.category == "out_of_scope"
        if general_retrieve is not None and is_general_topic:
            sources = await general_retrieve(state["query"])
        else:
            sources = await retrieve(state["query"])
        return {"evidence": format_evidence(sources), "evidence_sources": list(sources)}

    return retriever
