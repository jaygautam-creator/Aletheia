"""Offline tests for the FEVER corpus connector.

The connector parses FEVER's ``wiki-pages`` JSONL lines; these build small,
FEVER-shaped records in the test, so no dataset is downloaded or redistributed.
"""

from __future__ import annotations

import json

import pytest

from aletheia.corpus.connectors import CONNECTORS
from aletheia.corpus.connectors.fever import FEVER_LICENSE, FeverConnector, clean_wiki_markup


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


def test_folds_penn_treebank_markup_so_evidence_is_quotable() -> None:
    # The real failure mode: FEVER stores "-LRB- ... -RRB-" and space-separated
    # punctuation, which a weak model rewrites to plain text while copying a span,
    # so the verbatim guard then rejects a correct quote. Ingestion must fold it.
    raw = _line(
        id="Peking_University",
        text="ignored",
        lines="0\tPeking University -LRB- abbreviated PKU -RRB- is in Beijing , China .",
    )

    (source,) = FeverConnector().parse(raw)

    body = next(document for document in source.documents if document.kind == "body")
    assert body.text == "Peking University (abbreviated PKU) is in Beijing, China."


def test_folds_markup_in_the_title_but_never_in_the_page_id() -> None:
    # The title is a retrievable document of its own, so it needs the same fold as the
    # body. ``external_id`` must survive raw: the benchmark joins corpus coverage on the
    # page id, and folding it there would break that join silently.
    raw = _line(id="Yadu_-LRB-poetry-RRB-", text="ignored", lines="0\tA form of verse .")

    (source,) = FeverConnector().parse(raw)

    assert source.title == "Yadu (poetry)"
    assert source.external_id == "Yadu_-LRB-poetry-RRB-"
    title = next(document for document in source.documents if document.kind == "title")
    assert title.text == "Yadu (poetry)"


def test_clean_wiki_markup_folds_all_bracket_tokens_and_spacing() -> None:
    assert clean_wiki_markup("a -LSB- b -RSB- -LCB- c -RCB-") == "a [b] {c}"
    assert clean_wiki_markup("UIC is a state-funded university , located in Chicago .") == (
        "UIC is a state-funded university, located in Chicago."
    )
    assert clean_wiki_markup("ratio -COLON- high") == "ratio: high"


def test_clean_wiki_markup_leaves_plain_text_untouched() -> None:
    plain = "The University of Illinois at Chicago is state-funded."
    assert clean_wiki_markup(plain) == plain


def test_connector_is_registered_under_its_name() -> None:
    assert CONNECTORS["fever"] is FeverConnector


async def test_fetch_is_disabled_with_a_helpful_message() -> None:
    with pytest.raises(NotImplementedError, match="wiki-pages"):
        await FeverConnector().fetch(["Some_Page"])
