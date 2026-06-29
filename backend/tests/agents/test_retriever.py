"""Tests for the Retriever node — pass-through vs. corpus search, with a scripted search.

No database here: the node depends only on an injected ``EvidenceRetriever``, so a plain
async function stands in for the corpus. The database-backed search itself is covered by
the retrieval integration tests.
"""

from __future__ import annotations

from collections.abc import Sequence

from aletheia.agents.retriever import make_retriever_node
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence


def _source(text: str = "aspirin reduces fever") -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=1,
        source_id=1,
        connector="pubmed",
        external_id="1",
        title="A title",
        url=None,
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text=text,
        score=0.5,
    )


async def test_node_passes_through_when_evidence_is_already_present() -> None:
    calls: list[str] = []

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        calls.append(query)
        return [_source()]

    node = make_retriever_node(retrieve)
    out = await node({"query": "q", "evidence": "caller-supplied evidence"})

    # Caller's evidence is respected and no search runs.
    assert out == {}
    assert calls == []


async def test_node_searches_and_formats_when_evidence_is_absent() -> None:
    source = _source("aspirin reduces fever in adults")

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return [source]

    node = make_retriever_node(retrieve)
    out = await node({"query": "does aspirin reduce fever?"})

    assert out["evidence_sources"] == [source]
    # The chunk text is carried verbatim so the Verifier can quote it.
    assert "aspirin reduces fever in adults" in out["evidence"]


async def test_node_handles_no_hits_with_empty_evidence() -> None:
    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return []

    node = make_retriever_node(retrieve)
    out = await node({"query": "nothing matches this"})

    # No hits leaves the Verifier with nothing to ground in — every verdict becomes
    # Unverifiable downstream, which is the safe outcome.
    assert out["evidence"] == ""
    assert out["evidence_sources"] == []
