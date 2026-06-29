"""Offline tests for the pure retrieval logic — RRF fusion and evidence assembly.

The two SQL branches need a real PostgreSQL (pgvector / tsvector) and are covered by the
integration tests; here we exercise :func:`reciprocal_rank_fusion` and :func:`to_evidence`,
which are pure and need no database.
"""

from __future__ import annotations

import pytest

from aletheia.corpus.models import Chunk, Document, Source, TrustTier
from aletheia.corpus.retrieval import reciprocal_rank_fusion, to_evidence


def test_single_ranking_preserves_order() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"]])

    assert [item for item, _ in fused] == ["a", "b", "c"]
    # Scores strictly decrease with rank.
    scores = [score for _, score in fused]
    assert scores == sorted(scores, reverse=True)


def test_agreement_beats_a_lone_top_rank() -> None:
    # "b" is never first, but both branches rank it; "a" is first in only one branch.
    # RRF's defining property: consensus across branches outranks a single strong hit.
    fused = reciprocal_rank_fusion([["a", "b"], ["c", "b"]])

    assert fused[0][0] == "b"


def test_item_in_both_lists_sums_its_contributions() -> None:
    fused = dict(reciprocal_rank_fusion([["x"], ["x"]], k=60))

    # rank 1 in each list: 1/(60+1) summed twice.
    assert fused["x"] == pytest.approx(2.0 / 61.0)


def test_missing_items_contribute_nothing_and_are_ranked_last() -> None:
    fused = reciprocal_rank_fusion([["a", "b"], ["a"]])
    by_item = dict(fused)

    assert by_item["a"] == pytest.approx(1.0 / 61.0 + 1.0 / 61.0)
    assert by_item["b"] == pytest.approx(1.0 / 62.0)
    assert fused[0][0] == "a"


def test_ties_break_by_first_appearance_deterministically() -> None:
    # Both appear once at rank 1, so scores tie; order follows first appearance.
    assert reciprocal_rank_fusion([["a"], ["b"]]) == reciprocal_rank_fusion([["a"], ["b"]])
    assert [item for item, _ in reciprocal_rank_fusion([["a"], ["b"]])] == ["a", "b"]


def test_empty_input_yields_empty_fusion() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


@pytest.mark.parametrize("k", [0, -1])
def test_non_positive_k_is_rejected(k: int) -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=k)


def _chunk(chunk_id: int, *, text: str, tier: TrustTier = TrustTier.CURATED_CORPUS) -> Chunk:
    """Build a transient chunk wired to its document and source, with ids set."""
    source = Source(
        connector="pubmed",
        external_id=f"pmid-{chunk_id}",
        title=f"Title {chunk_id}",
        url=f"https://example.test/{chunk_id}",
        trust_tier=tier,
        meta={},
    )
    source.id = chunk_id * 100
    document = Document(kind="abstract", ordinal=0, text=text)
    document.id = chunk_id * 10
    document.source = source
    chunk = Chunk(ordinal=0, text=text, embedding=None)
    chunk.id = chunk_id
    chunk.document = document
    return chunk


def test_to_evidence_carries_provenance_and_trust_tier() -> None:
    chunk = _chunk(1, text="aspirin reduces fever")

    [evidence] = to_evidence([(1, 0.5)], {1: chunk})

    assert evidence.chunk_id == 1
    assert evidence.source_id == 100
    assert evidence.connector == "pubmed"
    assert evidence.external_id == "pmid-1"
    assert evidence.title == "Title 1"
    assert evidence.url == "https://example.test/1"
    assert evidence.trust_tier is TrustTier.CURATED_CORPUS
    assert evidence.kind == "abstract"
    assert evidence.text == "aspirin reduces fever"
    assert evidence.score == 0.5


def test_to_evidence_preserves_ranking_order() -> None:
    chunks = {cid: _chunk(cid, text=f"text {cid}") for cid in (1, 2, 3)}

    evidence = to_evidence([(2, 0.9), (3, 0.6), (1, 0.3)], chunks)

    assert [item.chunk_id for item in evidence] == [2, 3, 1]


def test_to_evidence_skips_unknown_chunk_ids() -> None:
    chunks = {1: _chunk(1, text="present")}

    evidence = to_evidence([(99, 0.9), (1, 0.5)], chunks)

    assert [item.chunk_id for item in evidence] == [1]
