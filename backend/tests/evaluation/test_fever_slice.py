"""Offline tests for the FEVER corpus-slice builder (ADR-0011).

:func:`build_corpus_slice` is pure (ids in, ids out) and exercised with hand-built
:class:`BenchmarkItem`s. The dump-reading half is exercised against tiny fabricated
shard files in ``tmp_path`` — never the real multi-gigabyte FEVER dump.
"""

from __future__ import annotations

import json
from pathlib import Path

from aletheia.agents.contracts import Verdict
from aletheia.evaluation.benchmark import BenchmarkItem
from aletheia.evaluation.fever_slice import (
    build_corpus_slice,
    build_slice_manifest,
    index_wiki_pages,
    write_corpus_slice_file,
)


def _item(id_: str, gold: Verdict, cited: list[str] | None = None) -> BenchmarkItem:
    return BenchmarkItem(
        id=id_, claim=f"claim {id_}", gold=gold, cited_doc_ids=cited or [], dataset="fever"
    )


def test_slice_includes_every_cited_page_from_the_sample() -> None:
    claims = [
        _item("1", Verdict.SUPPORTED, ["Page_A"]),
        _item("2", Verdict.CONTRADICTED, ["Page_B", "Page_C"]),
        _item("3", Verdict.UNVERIFIABLE),
    ]
    pool = ["Page_A", "Page_B", "Page_C", "Distractor_1", "Distractor_2"]

    slice_ = build_corpus_slice(claims, pool, sample_size=3, seed=7, corpus_target=5)

    assert set(slice_.evidence_page_ids) == {"Page_A", "Page_B", "Page_C"}
    assert len(slice_.distractor_page_ids) == 2  # tops up to corpus_target=5
    assert set(slice_.page_ids) == {
        "Page_A",
        "Page_B",
        "Page_C",
        "Distractor_1",
        "Distractor_2",
    }


def test_distractors_never_duplicate_evidence_pages() -> None:
    claims = [_item("1", Verdict.SUPPORTED, ["Page_A"])]
    pool = ["Page_A", "Page_B"]

    slice_ = build_corpus_slice(claims, pool, sample_size=1, seed=7, corpus_target=5)

    assert "Page_A" not in slice_.distractor_page_ids
    assert slice_.distractor_page_ids == ("Page_B",)


def test_is_deterministic_for_a_given_seed() -> None:
    claims = [_item(str(i), Verdict.UNVERIFIABLE) for i in range(5)]
    pool = [f"Distractor_{i}" for i in range(20)]

    first = build_corpus_slice(claims, pool, sample_size=3, seed=7, corpus_target=8)
    second = build_corpus_slice(claims, pool, sample_size=3, seed=7, corpus_target=8)

    assert first.page_ids == second.page_ids
    assert first.claims == second.claims


def test_corpus_target_smaller_than_evidence_adds_no_distractors() -> None:
    claims = [_item("1", Verdict.SUPPORTED, ["Page_A", "Page_B", "Page_C"])]
    pool = ["Page_A", "Page_B", "Page_C", "Distractor_1"]

    slice_ = build_corpus_slice(claims, pool, sample_size=1, seed=7, corpus_target=1)

    assert slice_.distractor_page_ids == ()


def test_manifest_records_slice_parameters_and_totals() -> None:
    claims = [_item("1", Verdict.SUPPORTED, ["Page_A"])]
    pool = ["Page_A", "Distractor_1"]
    slice_ = build_corpus_slice(claims, pool, sample_size=1, seed=7, corpus_target=2)

    manifest = build_slice_manifest(slice_, seed=7, sample_size=1, corpus_target=2)

    assert manifest.to_dict() == {
        "dataset": "fever",
        "sample_size": 1,
        "seed": 7,
        "corpus_target": 2,
        "claim_count": 1,
        "evidence_page_count": 1,
        "distractor_page_count": 1,
        "total_page_count": 2,
        "caveat": manifest.to_dict()["caveat"],  # presence checked; wording is prose
    }


def _wiki_line(page_id: str, sentence: str) -> str:
    return json.dumps({"id": page_id, "text": sentence, "lines": f"0\t{sentence}"})


def test_index_wiki_pages_maps_ids_across_shards(tmp_path: Path) -> None:
    (tmp_path / "wiki-001.jsonl").write_text(
        _wiki_line("Page_A", "a") + "\n" + _wiki_line("Page_B", "b") + "\n", "utf-8"
    )
    (tmp_path / "wiki-002.jsonl").write_text(_wiki_line("Page_C", "c") + "\n", "utf-8")

    index = index_wiki_pages(tmp_path)

    assert set(index) == {"Page_A", "Page_B", "Page_C"}
    assert index["Page_C"] == tmp_path / "wiki-002.jsonl"


def test_write_corpus_slice_file_writes_only_requested_pages(tmp_path: Path) -> None:
    (tmp_path / "wiki-001.jsonl").write_text(
        _wiki_line("Page_A", "a") + "\n" + _wiki_line("Page_B", "b") + "\n", "utf-8"
    )
    index = index_wiki_pages(tmp_path)
    output = tmp_path / "corpus_fever.jsonl"

    written = write_corpus_slice_file(["Page_A"], index, output)

    assert written == 1
    (line,) = output.read_text("utf-8").splitlines()
    assert json.loads(line)["id"] == "Page_A"


def test_write_corpus_slice_file_skips_ids_missing_from_the_index(tmp_path: Path) -> None:
    (tmp_path / "wiki-001.jsonl").write_text(_wiki_line("Page_A", "a") + "\n", "utf-8")
    index = index_wiki_pages(tmp_path)
    output = tmp_path / "corpus_fever.jsonl"

    written = write_corpus_slice_file(["Page_A", "Missing_Page"], index, output)

    assert written == 1
