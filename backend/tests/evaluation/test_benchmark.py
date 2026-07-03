"""Offline tests for the SciFact benchmark adapter, sampling, and coverage check.

These exercise the label mapping, the JSONL loader, the seeded stratified sampler, and
the corpus-coverage set logic with small, hand-built inputs — no dataset is downloaded
or redistributed, and nothing touches a database.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.benchmark import (
    BenchmarkItem,
    coverage_against,
    load_scifact_claims,
    parse_scifact_claim,
    stratified_sample,
)


def _line(**fields: object) -> str:
    return json.dumps(fields)


def test_support_evidence_maps_to_supported() -> None:
    item = parse_scifact_claim(
        _line(
            id=1,
            claim="Low-dose aspirin lowers cardiovascular risk.",
            evidence={"42": [{"sentences": [0], "label": "SUPPORT"}]},
            cited_doc_ids=[42],
        )
    )

    assert item.gold is Verdict.SUPPORTED
    assert item.id == "1"  # numeric ids are normalised to strings
    assert item.cited_doc_ids == ["42"]
    assert item.dataset == "scifact"


def test_contradict_evidence_maps_to_contradicted() -> None:
    item = parse_scifact_claim(
        _line(
            id=2,
            claim="Vitamin C cures the common cold.",
            evidence={"7": [{"sentences": [1], "label": "CONTRADICT"}]},
        )
    )

    assert item.gold is Verdict.CONTRADICTED


def test_absent_evidence_maps_to_unverifiable() -> None:
    # SciFact's NotEnoughInfo claims carry an empty evidence map.
    item = parse_scifact_claim(_line(id=3, claim="A claim with no cited evidence.", evidence={}))

    assert item.gold is Verdict.UNVERIFIABLE
    assert item.cited_doc_ids == []


def test_contradict_takes_precedence_over_support() -> None:
    item = parse_scifact_claim(
        _line(
            id=4,
            claim="A claim with mixed evidence.",
            evidence={"1": [{"label": "SUPPORT"}], "2": [{"label": "CONTRADICT"}]},
        )
    )

    assert item.gold is Verdict.CONTRADICTED


def test_load_reads_every_nonblank_line(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text(
        _line(id=1, claim="supported", evidence={"1": [{"label": "SUPPORT"}]})
        + "\n\n"  # a blank line in the middle is ignored
        + _line(id=2, claim="not enough info", evidence={})
        + "\n",
        "utf-8",
    )

    items = load_scifact_claims(path)

    assert [item.gold for item in items] == [Verdict.SUPPORTED, Verdict.UNVERIFIABLE]


def test_load_rejects_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("\n   \n", "utf-8")

    with pytest.raises(ValueError, match="No SciFact claims"):
        load_scifact_claims(path)


def _item(id_: int, gold: Verdict, cited: list[str] | None = None) -> BenchmarkItem:
    return BenchmarkItem(id=str(id_), claim=f"claim {id_}", gold=gold, cited_doc_ids=cited or [])


def _mixed_items() -> list[BenchmarkItem]:
    """60 items: 30 Supported, 20 Contradicted, 10 Unverifiable, interleaved."""
    labels = [Verdict.SUPPORTED] * 30 + [Verdict.CONTRADICTED] * 20 + [Verdict.UNVERIFIABLE] * 10
    return [_item(i, gold) for i, gold in enumerate(labels)]


def test_stratified_sample_is_deterministic_for_a_seed() -> None:
    items = _mixed_items()

    first = stratified_sample(items, 12, seed=7)
    second = stratified_sample(items, 12, seed=7)

    assert [item.id for item in first] == [item.id for item in second]


def test_stratified_sample_keeps_the_gold_label_proportions() -> None:
    # 30/20/10 of 60 sampled down to 6 should allocate exactly 3/2/1.
    sample = stratified_sample(_mixed_items(), 6, seed=7)

    counts = {gold: sum(1 for item in sample if item.gold is gold) for gold in Verdict}
    assert counts[Verdict.SUPPORTED] == 3
    assert counts[Verdict.CONTRADICTED] == 2
    assert counts[Verdict.UNVERIFIABLE] == 1


def test_stratified_sample_gives_the_rounding_remainder_to_the_largest_stratum() -> None:
    # 5 S / 3 C / 2 U sampled to n=4 floors to 2/1/0 with one left over — the
    # largest stratum (Supported) absorbs it: 3/1/0.
    labels = [Verdict.SUPPORTED] * 5 + [Verdict.CONTRADICTED] * 3 + [Verdict.UNVERIFIABLE] * 2
    items = [_item(i, gold) for i, gold in enumerate(labels)]

    sample = stratified_sample(items, 4, seed=7)

    counts = {gold: sum(1 for item in sample if item.gold is gold) for gold in Verdict}
    assert len(sample) == 4
    assert counts[Verdict.SUPPORTED] == 3
    assert counts[Verdict.CONTRADICTED] == 1
    assert counts[Verdict.UNVERIFIABLE] == 0


def test_stratified_sample_preserves_dataset_order() -> None:
    items = _mixed_items()

    sample = stratified_sample(items, 12, seed=7)

    positions = [int(item.id) for item in sample]
    assert positions == sorted(positions)


def test_stratified_sample_returns_everything_when_n_is_large_enough() -> None:
    items = _mixed_items()

    assert stratified_sample(items, len(items), seed=7) == items
    assert stratified_sample(items, len(items) + 5, seed=7) == items


def test_stratified_sample_rejects_a_negative_n() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        stratified_sample(_mixed_items(), -1, seed=7)


def test_coverage_counts_items_whose_cited_docs_are_all_ingested() -> None:
    items = [
        _item(1, Verdict.SUPPORTED, cited=["10", "11"]),  # both present -> covered
        _item(2, Verdict.CONTRADICTED, cited=["10", "99"]),  # one missing -> not covered
        _item(3, Verdict.UNVERIFIABLE),  # cites nothing -> trivially covered
    ]

    coverage = coverage_against(items, {"10", "11", "12"})

    assert coverage.n_items == 3
    assert coverage.n_covered == 2
    assert coverage.fraction == pytest.approx(2 / 3)


def test_coverage_of_an_empty_claim_set_is_vacuously_full() -> None:
    coverage = coverage_against([], {"10"})

    assert coverage.n_items == 0
    assert coverage.fraction == 1.0
