"""Offline tests for the FEVER corpus connector.

The connector parses FEVER's ``wiki-pages`` JSONL lines; these build small,
FEVER-shaped records in the test, so no dataset is downloaded or redistributed.
"""

from __future__ import annotations

import json

import pytest

from aletheia.corpus.connectors import CONNECTORS
from aletheia.corpus.connectors.fever import FEVER_LICENSE, FeverConnector


def _line(**fields: object) -> str:
    return json.dumps(fields)


def test_parses_title_and_body_stripping_indices_and_links() -> None:
    raw = _line(
        id="Nikolaj_Coster-Waldau",
        text="ignored — the connector reads lines, not text",
        lines=(
            "0\tNikolaj William Coster-Waldau is a Danish actor.\tNikolaj Coster-Waldau\tDanish\n"
            "1\tHe starred in Game of Thrones.\tGame of Thrones"
        ),
    )

    (source,) = FeverConnector().parse(raw)

    assert source.connector == "fever"
    assert source.external_id == "Nikolaj_Coster-Waldau"
    assert source.title == "Nikolaj Coster-Waldau"  # underscores become spaces
    assert source.license == FEVER_LICENSE
    assert [document.kind for document in source.documents] == ["title", "body"]
    body = next(document for document in source.documents if document.kind == "body")
    assert body.text == (
        "Nikolaj William Coster-Waldau is a Danish actor. He starred in Game of Thrones."
    )


def test_blank_and_index_only_rows_are_skipped() -> None:
    raw = _line(id="Empty_Page", text="", lines="0\t\n1\tOne real sentence.\n2\t")

    (source,) = FeverConnector().parse(raw)

    body = next(document for document in source.documents if document.kind == "body")
    assert body.text == "One real sentence."


def test_page_without_lines_yields_only_a_title_document() -> None:
    (source,) = FeverConnector().parse(_line(id="Title_Only", text="x", lines=""))

    assert [document.kind for document in source.documents] == ["title"]


def test_skips_blank_lines_and_parses_every_record() -> None:
    raw = (
        _line(id="A", text="", lines="0\tx") + "\n\n" + _line(id="B", text="", lines="0\ty") + "\n"
    )

    sources = FeverConnector().parse(raw)

    assert [source.external_id for source in sources] == ["A", "B"]


def test_connector_is_registered_under_its_name() -> None:
    assert CONNECTORS["fever"] is FeverConnector


async def test_fetch_is_disabled_with_a_helpful_message() -> None:
    with pytest.raises(NotImplementedError, match="wiki-pages"):
        await FeverConnector().fetch(["Some_Page"])
