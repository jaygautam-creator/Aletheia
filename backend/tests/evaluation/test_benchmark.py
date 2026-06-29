"""Offline tests for the SciFact benchmark adapter.

These exercise the label mapping and the JSONL loader with small, SciFact-shaped lines
built in the test — no dataset is downloaded or redistributed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.benchmark import load_scifact_claims, parse_scifact_claim


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
