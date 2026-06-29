"""SciFact connector — biomedical abstracts from the SciFact corpus file.

SciFact (Wadden et al., *Fact or Fiction: Verifying Scientific Claims*, EMNLP 2020)
ships its evidence as a single ``corpus.jsonl`` of abstracts, not as an E-utilities
database, so this connector parses that bulk file rather than fetching by id. Each line
— ``{"doc_id", "title", "abstract": [sentences], "structured"}`` — becomes one
:class:`FetchedSource` with a title document and an abstract document (the sentences
joined), ready for the same chunk/embed/store pipeline as the NCBI connectors.

Ingesting it is how the frozen corpus grows to cover the benchmark (EVALUATION.md §4);
the licence (CC BY-NC 2.0) is recorded as provenance on every source.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from aletheia.corpus.connectors.base import FetchedSource, RawDocument, SourceConnector

#: SciFact is distributed under CC BY-NC 2.0; recorded on every source for provenance.
SCIFACT_LICENSE = "CC BY-NC 2.0"


class ScifactConnector(SourceConnector):
    """Normalizes SciFact ``corpus.jsonl`` lines into :class:`FetchedSource` records."""

    name = "scifact"
    db = "scifact"  # unused: SciFact is read from its corpus file, never fetched by id.

    def parse(self, raw: str) -> list[FetchedSource]:
        return [self._parse_line(line) for line in raw.splitlines() if line.strip()]

    async def fetch(self, external_ids: Sequence[str]) -> list[FetchedSource]:
        """SciFact has no per-id fetch endpoint — it is ingested from its corpus file."""
        raise NotImplementedError(
            "SciFact is distributed as a bulk corpus file; ingest it with "
            "--corpus-file path/to/corpus.jsonl rather than fetching by id."
        )

    def _parse_line(self, line: str) -> FetchedSource:
        record = json.loads(line)
        title = str(record.get("title") or "")
        sentences = record.get("abstract") or []
        abstract = " ".join(part.strip() for part in sentences if part.strip())

        documents: list[RawDocument] = []
        if title:
            documents.append(RawDocument(kind="title", text=title, ordinal=len(documents)))
        if abstract:
            documents.append(RawDocument(kind="abstract", text=abstract, ordinal=len(documents)))

        return FetchedSource(
            connector=self.name,
            external_id=str(record["doc_id"]),
            title=title,
            documents=tuple(documents),
            license=SCIFACT_LICENSE,
            meta={"structured": bool(record.get("structured", False))},
        )
