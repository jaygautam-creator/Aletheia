"""FEVER connector — Wikipedia pages from the FEVER wiki-pages dump.

FEVER (Thorne et al., *FEVER: a Large-scale Dataset for Fact Extraction and
VERification*, NAACL 2018) ships its evidence as sharded ``wiki-pages`` JSONL files, not
as an E-utilities database, so this connector parses those bulk files rather than
fetching by id. Each line — ``{"id", "text", "lines"}`` — becomes one
:class:`FetchedSource`. ``id`` is the Wikipedia page title (FEVER's page key, with
spaces as underscores); ``lines`` is a sentence-numbered dump (``"0\\tsentence
one\\tlink\\n1\\tsentence two\\n..."``) where each record is tab-separated
``index, sentence, [outgoing links...]``. The connector strips the indices and links,
keeping only the sentence text, joined into one body document — this is the same text
FEVER's own evidence annotations (``sentence_id``) index into (see ADR-0011).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from aletheia.corpus.connectors.base import FetchedSource, RawDocument, SourceConnector

#: FEVER's wiki-pages dump is derived from Wikipedia, licensed CC BY-SA 3.0.
FEVER_LICENSE = "CC BY-SA 3.0"


class FeverConnector(SourceConnector):
    """Normalizes FEVER ``wiki-pages`` JSONL lines into :class:`FetchedSource` records."""

    name = "fever"
    db = "fever"  # unused: FEVER is read from its wiki-pages dump, never fetched by id.

    def parse(self, raw: str) -> list[FetchedSource]:
        return [self._parse_line(line) for line in raw.splitlines() if line.strip()]

    async def fetch(self, external_ids: Sequence[str]) -> list[FetchedSource]:
        """FEVER has no per-id fetch endpoint — it is ingested from its wiki-pages dump."""
        raise NotImplementedError(
            "FEVER is distributed as sharded wiki-pages JSONL files; ingest it with "
            "--corpus-file path/to/wiki-pages/wiki-NNN.jsonl rather than fetching by id."
        )

    def _parse_line(self, line: str) -> FetchedSource:
        record = json.loads(line)
        page_id = str(record["id"])
        title = page_id.replace("_", " ")
        body = _sentences_from_lines(str(record.get("lines") or ""))

        documents: list[RawDocument] = []
        if title:
            documents.append(RawDocument(kind="title", text=title, ordinal=len(documents)))
        if body:
            documents.append(RawDocument(kind="body", text=body, ordinal=len(documents)))

        return FetchedSource(
            connector=self.name,
            external_id=page_id,
            title=title,
            documents=tuple(documents),
            license=FEVER_LICENSE,
            meta={},
        )


def _sentences_from_lines(lines_field: str) -> str:
    """Strip FEVER's per-sentence index and outgoing-link columns, joining the sentences.

    Each row of ``lines`` is ``index\\tsentence\\t[link\\tlink...]``; blank sentences
    (a dump artifact) are dropped. Malformed rows (missing the sentence column) are
    skipped rather than raised on, since a handful of dump rows are index-only.
    """
    sentences: list[str] = []
    for row in lines_field.split("\n"):
        if not row.strip():
            continue
        parts = row.split("\t")
        min_columns = 2  # index + sentence; outgoing links (if any) trail after
        if len(parts) < min_columns:
            continue
        sentence = parts[1].strip()
        if sentence:
            sentences.append(sentence)
    return " ".join(sentences)
