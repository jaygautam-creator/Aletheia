"""The Retriever node — where the corpus becomes the evidence the Verifier grounds in.

In Phase 1 the evidence was supplied with each request. From Phase 2 this node fills it
from the curated corpus: it searches for the query and formats the trust-tiered hits
into the single evidence block the Verifier checks against. The node is deliberately a
*pass-through when evidence is already present*, so the controlled evaluation (which
supplies its own evidence) and any caller that brings its own text are untouched — the
downstream contract does not change, retrieval is purely additive.

The node depends on an injected :data:`EvidenceRetriever` rather than a database session
so the graph stays unit-testable offline; the production retriever (pgvector + keyword
search over a live corpus) is wired in at the API edge.
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


def make_retriever_node(retrieve: EvidenceRetriever) -> RetrieverNode:
    """Build the Retriever node bound to a specific corpus search function."""

    async def retriever(state: PipelineState) -> PipelineState:
        # Respect evidence the caller already supplied (e.g. the evaluation harness):
        # only the empty/absent case triggers a corpus search.
        if state.get("evidence") is not None:
            return {}

        sources = await retrieve(state["query"])
        return {"evidence": format_evidence(sources), "evidence_sources": list(sources)}

    return retriever
