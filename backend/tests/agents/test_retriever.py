"""Tests for the Retriever node — pass-through vs. corpus search, with a scripted search.

No database here: the node depends only on an injected ``EvidenceRetriever``, so a plain
async function stands in for the corpus. The database-backed search itself is covered by
the retrieval integration tests.
"""

from __future__ import annotations

from collections.abc import Sequence

from aletheia.agents.intake import IntakeDecision
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


async def test_out_of_scope_intake_routes_to_the_general_retriever() -> None:
    # ADR-0012: an out-of-scope ruling picks the live-fallback search, not the corpus one.
    corpus_source = _source("corpus text")
    general_source = _source("wikipedia text")

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return [corpus_source]

    async def general_retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return [general_source]

    node = make_retriever_node(retrieve, general_retrieve=general_retrieve)
    out = await node(
        {
            "query": "who won the 1990 world cup?",
            "intake": IntakeDecision(allowed=True, category="out_of_scope", reason="general"),
        }
    )

    assert out["evidence_sources"] == [general_source]


async def test_in_scope_intake_still_uses_the_corpus_retriever() -> None:
    corpus_source = _source("corpus text")

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return [corpus_source]

    async def general_retrieve(query: str) -> Sequence[RetrievedEvidence]:
        raise AssertionError("the general retriever must not run for an in-scope query")

    node = make_retriever_node(retrieve, general_retrieve=general_retrieve)
    out = await node(
        {
            "query": "does aspirin help the heart?",
            "intake": IntakeDecision(allowed=True, category="ok", reason="in scope"),
        }
    )

    assert out["evidence_sources"] == [corpus_source]


async def test_no_general_retriever_configured_always_uses_the_corpus_one() -> None:
    # Without ADR-0012 wired in (general_retrieve=None), behavior is unchanged even for
    # an out-of-scope ruling.
    corpus_source = _source("corpus text")

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        return [corpus_source]

    node = make_retriever_node(retrieve)
    out = await node(
        {
            "query": "who won the 1990 world cup?",
            "intake": IntakeDecision(allowed=True, category="out_of_scope", reason="general"),
        }
    )

    assert out["evidence_sources"] == [corpus_source]
