"""Offline tests for the grounded-arm error analysis.

Every case is built from hand-made benchmark items and traces — no run is executed, no
model or database is touched — so the categorisation logic and the join can be pinned
down deterministically.
"""

from __future__ import annotations

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.benchmark import BenchmarkItem
from aletheia.evaluation.error_analysis import (
    Category,
    ErrorAnalysis,
    categorize,
    diagnose,
    render_markdown,
)
from aletheia.evaluation.trace import RetrievedSpan, RunTrace, VerdictTrace


def _item(id: str, claim: str, gold: Verdict, cited: list[str] | None = None) -> BenchmarkItem:
    return BenchmarkItem(id=id, claim=claim, gold=gold, cited_doc_ids=cited or [])


def _trace(
    claim: str, verdict: Verdict, *, evidence_ids: list[str], span: str | None = "x"
) -> RunTrace:
    return RunTrace(
        query=claim,
        candidate_answer=claim,
        latency_s=0.0,
        evidence=[
            RetrievedSpan(
                external_id=eid, title="t", trust_tier="curated_corpus", score=0.5, text="…"
            )
            for eid in evidence_ids
        ],
        verdicts=[VerdictTrace(claim=claim, verdict=str(verdict), quoted_span=span)],
        llm_calls=[],
    )


# --- categorize: one correct outcome and four mutually-exclusive miss causes -----------


def test_correct_when_prediction_matches_gold() -> None:
    for verdict in Verdict:
        assert categorize(verdict, verdict, retrieved_gold=True) is Category.CORRECT
        assert categorize(verdict, verdict, retrieved_gold=False) is Category.CORRECT


def test_unverifiable_without_retrieved_evidence_is_a_retrieval_miss() -> None:
    got = categorize(Verdict.SUPPORTED, Verdict.UNVERIFIABLE, retrieved_gold=False)
    assert got is Category.RETRIEVAL_MISS


def test_unverifiable_with_retrieved_evidence_is_a_verifier_abstention() -> None:
    got = categorize(Verdict.CONTRADICTED, Verdict.UNVERIFIABLE, retrieved_gold=True)
    assert got is Category.VERIFIER_ABSTENTION


def test_opposite_stance_is_wrong_direction_regardless_of_retrieval() -> None:
    assert categorize(Verdict.SUPPORTED, Verdict.CONTRADICTED, retrieved_gold=True) is (
        Category.WRONG_DIRECTION
    )
    assert categorize(Verdict.CONTRADICTED, Verdict.SUPPORTED, retrieved_gold=False) is (
        Category.WRONG_DIRECTION
    )


def test_asserting_a_notenoughinfo_claim_is_false_grounding() -> None:
    assert categorize(Verdict.UNVERIFIABLE, Verdict.SUPPORTED, retrieved_gold=True) is (
        Category.FALSE_GROUNDING
    )
    assert categorize(Verdict.UNVERIFIABLE, Verdict.CONTRADICTED, retrieved_gold=True) is (
        Category.FALSE_GROUNDING
    )


# --- diagnose: the join and the retrieved-gold determination ---------------------------


def test_retrieved_gold_true_when_cited_abstract_was_retrieved() -> None:
    items = [_item("1", "claim a", Verdict.SUPPORTED, cited=["DOC1"])]
    traces = [_trace("claim a", Verdict.UNVERIFIABLE, evidence_ids=["DOC1", "DOC2"])]
    analysis = diagnose(items, traces)
    (diag,) = analysis.diagnoses
    assert diag.retrieved_gold is True
    assert diag.category is Category.VERIFIER_ABSTENTION


def test_retrieved_gold_false_when_cited_abstract_missing_from_evidence() -> None:
    items = [_item("1", "claim a", Verdict.SUPPORTED, cited=["DOC1"])]
    traces = [_trace("claim a", Verdict.UNVERIFIABLE, evidence_ids=["DOC9"])]
    analysis = diagnose(items, traces)
    (diag,) = analysis.diagnoses
    assert diag.retrieved_gold is False
    assert diag.category is Category.RETRIEVAL_MISS


def test_notenoughinfo_claim_is_vacuously_retrieved() -> None:
    items = [_item("1", "nei claim", Verdict.UNVERIFIABLE, cited=[])]
    traces = [_trace("nei claim", Verdict.UNVERIFIABLE, evidence_ids=["DOC1"])]
    analysis = diagnose(items, traces)
    (diag,) = analysis.diagnoses
    assert diag.retrieved_gold is True
    assert diag.category is Category.CORRECT


def test_join_is_by_claim_text_not_order() -> None:
    items = [
        _item("1", "first", Verdict.SUPPORTED, cited=["A"]),
        _item("2", "second", Verdict.CONTRADICTED, cited=["B"]),
    ]
    # Traces in the opposite order to the items.
    traces = [
        _trace("second", Verdict.CONTRADICTED, evidence_ids=["B"]),
        _trace("first", Verdict.SUPPORTED, evidence_ids=["A"]),
    ]
    analysis = diagnose(items, traces)
    assert [d.item_id for d in analysis.diagnoses] == ["1", "2"]
    assert all(d.category is Category.CORRECT for d in analysis.diagnoses)


def test_items_without_a_trace_are_reported_missing_not_scored() -> None:
    items = [
        _item("1", "present", Verdict.SUPPORTED, cited=["A"]),
        _item("2", "absent", Verdict.SUPPORTED, cited=["B"]),
    ]
    traces = [_trace("present", Verdict.SUPPORTED, evidence_ids=["A"])]
    analysis = diagnose(items, traces)
    assert analysis.missing == ["2"]
    assert analysis.n_scored == 1


# --- aggregation and rendering ---------------------------------------------------------


def _mixed_analysis() -> ErrorAnalysis:
    items = [
        _item("1", "c1", Verdict.SUPPORTED, cited=["A"]),  # correct
        _item("2", "c2", Verdict.SUPPORTED, cited=["B"]),  # verifier abstention
        _item("3", "c3", Verdict.CONTRADICTED, cited=["C"]),  # retrieval miss
        _item("4", "c4", Verdict.UNVERIFIABLE, cited=[]),  # false grounding
    ]
    traces = [
        _trace("c1", Verdict.SUPPORTED, evidence_ids=["A"]),
        _trace("c2", Verdict.UNVERIFIABLE, evidence_ids=["B"]),
        _trace("c3", Verdict.UNVERIFIABLE, evidence_ids=["Z"]),
        _trace("c4", Verdict.SUPPORTED, evidence_ids=["Q"]),
    ]
    return diagnose(items, traces)


def test_counts_and_accuracy() -> None:
    analysis = _mixed_analysis()
    counts = analysis.counts()
    assert counts[Category.CORRECT] == 1
    assert counts[Category.VERIFIER_ABSTENTION] == 1
    assert counts[Category.RETRIEVAL_MISS] == 1
    assert counts[Category.FALSE_GROUNDING] == 1
    assert analysis.n_scored == 4
    assert analysis.n_correct == 1
    assert analysis.accuracy == 0.25


def test_by_gold_partitions_the_diagnoses() -> None:
    analysis = _mixed_analysis()
    supported = analysis.by_gold(Verdict.SUPPORTED)
    assert supported[Category.CORRECT] == 1
    assert supported[Category.VERIFIER_ABSTENTION] == 1
    assert analysis.by_gold(Verdict.UNVERIFIABLE)[Category.FALSE_GROUNDING] == 1


def test_render_markdown_contains_tables_and_examples() -> None:
    out = render_markdown(_mixed_analysis(), examples=3)
    assert "| Outcome | Claims | Share |" in out
    assert "| Gold label | n | Correct |" in out
    assert "accuracy 25.0%" in out
    assert "Example" in out  # at least one miss category quoted


def test_render_markdown_omits_examples_when_disabled() -> None:
    out = render_markdown(_mixed_analysis(), examples=0)
    assert "Example" not in out


def test_render_markdown_flags_missing_items() -> None:
    items = [
        _item("1", "present", Verdict.SUPPORTED, cited=["A"]),
        _item("2", "absent", Verdict.SUPPORTED),
    ]
    traces = [_trace("present", Verdict.SUPPORTED, evidence_ids=["A"])]
    out = render_markdown(diagnose(items, traces))
    assert "no matching trace" in out
    assert "2" in out
