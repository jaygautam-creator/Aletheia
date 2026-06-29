"""End-to-end test of the verification graph on a planted unsupported claim.

This is the thesis in miniature: the Generator splits the answer into claims, the
Verifier grounds each against the evidence, and the one claim that has no supporting
span is flagged rather than waved through — even though the model "asserted" support
for it with a fabricated quote.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aletheia.agents import Verdict, VerificationPipeline
from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence
from aletheia.llm import FakeLLMClient

EVIDENCE = "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911."
ANSWER = "Marie Curie won the 1903 Nobel Prize in Physics. She also discovered penicillin."

# One generator call, then one verifier call per claim, in claim order.
_SCRIPT = [
    '{"claims": ["Marie Curie won the 1903 Nobel Prize in Physics.", '
    '"Marie Curie discovered penicillin."]}',
    '{"verdict": "Supported", "quoted_span": "Nobel Prize in Physics in 1903", '
    '"reasoning": "Stated by the evidence."}',
    # The planted claim: the model fabricates a quote to "support" it.
    '{"verdict": "Supported", "quoted_span": "discovered penicillin", '
    '"reasoning": "Fabricated support."}',
]


async def test_pipeline_catches_the_unsupported_claim() -> None:
    llm = FakeLLMClient(_SCRIPT)
    pipeline = VerificationPipeline(llm)

    result = await pipeline.run(
        query="What is Marie Curie known for?",
        evidence=EVIDENCE,
        candidate_answer=ANSWER,
    )

    assert llm.call_count == 3
    assert result.candidate_answer == ANSWER
    assert len(result.verdicts) == 2

    # First claim is genuinely grounded; second is caught despite the fabricated quote.
    assert result.verdicts[0].verdict is Verdict.SUPPORTED
    assert result.verdicts[1].verdict is Verdict.UNVERIFIABLE
    assert result.verdicts[1].quoted_span is None

    assert result.has_unsupported_claims
    assert [v.claim for v in result.flagged] == ["Marie Curie discovered penicillin."]
    assert result.support_ratio == 0.5


ASPIRIN_CHUNK = "Low-dose aspirin reduces cardiovascular risk in older adults."


def _aspirin_source() -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=1,
        source_id=1,
        connector="pubmed",
        external_id="1",
        title="Aspirin trial",
        url="https://example.test/1",
        trust_tier=TrustTier.CURATED_CORPUS,
        kind="abstract",
        text=ASPIRIN_CHUNK,
        score=0.42,
    )


async def test_pipeline_retrieves_evidence_when_none_is_supplied() -> None:
    queries: list[str] = []

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        queries.append(query)
        return [_aspirin_source()]

    llm = FakeLLMClient(
        [
            '{"claims": ["Aspirin reduces cardiovascular risk."]}',
            '{"verdict": "Supported", "quoted_span": "aspirin reduces cardiovascular risk", '
            '"reasoning": "Stated by the evidence."}',
        ]
    )
    pipeline = VerificationPipeline(llm, retrieve=retrieve)

    state = await pipeline.ainvoke(
        query="Does aspirin help the heart?",
        candidate_answer="Aspirin reduces cardiovascular risk.",
    )

    # The retriever searched for the query and its hit became the grounding evidence.
    assert queries == ["Does aspirin help the heart?"]
    assert state["evidence_sources"] == [_aspirin_source()]
    assert ASPIRIN_CHUNK in state["evidence"]
    assert state["result"].verdicts[0].verdict is Verdict.SUPPORTED


async def test_pipeline_does_not_retrieve_when_evidence_is_supplied() -> None:
    searched = False

    async def retrieve(query: str) -> Sequence[RetrievedEvidence]:
        nonlocal searched
        searched = True
        return []

    llm = FakeLLMClient(
        [
            '{"claims": ["Marie Curie won the 1903 Nobel Prize in Physics."]}',
            '{"verdict": "Supported", "quoted_span": "Nobel Prize in Physics in 1903", '
            '"reasoning": "Stated by the evidence."}',
        ]
    )
    pipeline = VerificationPipeline(llm, retrieve=retrieve)

    await pipeline.run(
        query="What is Marie Curie known for?",
        evidence=EVIDENCE,
        candidate_answer="Marie Curie won the 1903 Nobel Prize in Physics.",
    )

    assert searched is False


async def test_run_requires_evidence_without_a_retriever() -> None:
    pipeline = VerificationPipeline(FakeLLMClient([]))

    with pytest.raises(ValueError, match="evidence is required"):
        await pipeline.run(query="anything")
