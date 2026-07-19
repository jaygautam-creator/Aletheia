"""Offline tests for the FEVER benchmark adapter (ADR-0011).

Mirrors ``test_benchmark.py``'s SciFact coverage: the label mapping and the JSONL
loader, exercised with small, hand-built FEVER-shaped inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.benchmark import load_fever_claims, parse_fever_claim


def _line(**fields: object) -> str:
    return json.dumps(fields)


def test_supports_maps_to_supported() -> None:
    item = parse_fever_claim(
        _line(
            id=1,
            claim="Nikolaj Coster-Waldau worked with the Fox Broadcasting Company.",
            label="SUPPORTS",
            evidence=[[[100, 200, "Nikolaj_Coster-Waldau", 7]]],
        )
    )

    assert item.gold is Verdict.SUPPORTED
    assert item.id == "1"  # numeric ids are normalised to strings
    assert item.cited_doc_ids == ["Nikolaj_Coster-Waldau"]
    assert item.dataset == "fever"


def test_refutes_maps_to_contradicted() -> None:
    item = parse_fever_claim(
        _line(
            id=2,
            claim="Telemundo is a solely English-language channel.",
            label="REFUTES",
            evidence=[[[101, 201, "Telemundo", 0]]],
        )
    )

    assert item.gold is Verdict.CONTRADICTED


def test_not_enough_info_maps_to_unverifiable_with_no_citations() -> None:
    # FEVER's NEI claims carry an evidence row with a null page/sentence id.
    item = parse_fever_claim(
        _line(
            id=3,
            claim="A claim with no verifiable evidence.",
            label="NOT ENOUGH INFO",
            evidence=[[[102, None, None, None]]],
        )
    )

    assert item.gold is Verdict.UNVERIFIABLE
    assert item.cited_doc_ids == []


def test_cited_doc_ids_dedupe_across_multiple_evidence_sets() -> None:
    # Two OR'd evidence sets both citing the same page, plus one citing a second page.
    item = parse_fever_claim(
        _line(
            id=4,
            claim="A claim provable two ways.",
            label="SUPPORTS",
            evidence=[
                [[1, 1, "Page_A", 0], [1, 2, "Page_B", 1]],
                [[2, 3, "Page_A", 2]],
            ],
        )
    )

    assert item.cited_doc_ids == ["Page_A", "Page_B"]


def test_load_reads_every_nonblank_line(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text(
        _line(id=1, claim="a", label="SUPPORTS", evidence=[[[1, 1, "P", 0]]])
        + "\n\n"  # a blank line in the middle is ignored
        + _line(id=2, claim="b", label="NOT ENOUGH INFO", evidence=[[[2, None, None, None]]])
        + "\n",
        "utf-8",
    )

    items = load_fever_claims(path)

    assert [item.gold for item in items] == [Verdict.SUPPORTED, Verdict.UNVERIFIABLE]


def test_load_rejects_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("\n   \n", "utf-8")

    with pytest.raises(ValueError, match="No FEVER claims"):
        load_fever_claims(path)
