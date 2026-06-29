"""Offline tests for the SciFact corpus connector.

The connector parses SciFact's ``corpus.jsonl`` lines; these build small, SciFact-shaped
records in the test, so no dataset is downloaded or redistributed.
"""

from __future__ import annotations

import json

import pytest

from aletheia.corpus.connectors import CONNECTORS
from aletheia.corpus.connectors.scifact import SCIFACT_LICENSE, ScifactConnector


def _line(**fields: object) -> str:
    return json.dumps(fields)


def test_parses_title_and_abstract_into_documents() -> None:
    raw = _line(
        doc_id=42,
        title="Aspirin and the heart",
        abstract=["Low-dose aspirin reduces risk.", "Effects vary by age."],
        structured=False,
    )

    (source,) = ScifactConnector().parse(raw)

    assert source.connector == "scifact"
    assert source.external_id == "42"  # numeric doc_id is normalised to a string
    assert source.title == "Aspirin and the heart"
    assert source.license == SCIFACT_LICENSE
    assert [document.kind for document in source.documents] == ["title", "abstract"]
    abstract = next(document for document in source.documents if document.kind == "abstract")
    # The list of abstract sentences is joined into one document.
    assert abstract.text == "Low-dose aspirin reduces risk. Effects vary by age."


def test_skips_blank_lines_and_parses_every_record() -> None:
    raw = (
        _line(doc_id=1, title="A", abstract=["x"])
        + "\n\n"
        + _line(doc_id=2, title="B", abstract=["y"])
        + "\n"
    )

    sources = ScifactConnector().parse(raw)

    assert [source.external_id for source in sources] == ["1", "2"]


def test_record_without_an_abstract_yields_only_a_title_document() -> None:
    (source,) = ScifactConnector().parse(_line(doc_id=3, title="Title only", abstract=[]))

    assert [document.kind for document in source.documents] == ["title"]


def test_connector_is_registered_under_its_name() -> None:
    assert CONNECTORS["scifact"] is ScifactConnector


async def test_fetch_is_disabled_with_a_helpful_message() -> None:
    # SciFact has no per-id fetch endpoint; the error points at the corpus-file path.
    with pytest.raises(NotImplementedError, match="corpus-file"):
        await ScifactConnector().fetch(["1"])
