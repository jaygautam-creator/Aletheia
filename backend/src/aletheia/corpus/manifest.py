"""The corpus manifest: a committed, citable record of what was ingested.

For benchmark numbers to be reproducible, the corpus they ran against must be pinned
(ADR-0006). The manifest captures exactly that — the embedding model and width, the
trust tier, the list of ingested source IDs, and the document/chunk counts — as a small
JSON file committed alongside the code. Anyone can re-run the ingest from these IDs and
get the same corpus.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from aletheia.corpus.ingest import IngestReport
from aletheia.corpus.models import TrustTier

#: Bumped only when the manifest's shape changes, so readers can detect old files.
MANIFEST_SCHEMA_VERSION = 1


def build_manifest(
    report: IngestReport,
    *,
    provenance: str,
    generated_at: dt.datetime | None = None,
    trust_tier: TrustTier = TrustTier.CURATED_CORPUS,
) -> dict[str, Any]:
    """Build the manifest document from an :class:`IngestReport`.

    ``provenance`` records how the corpus was produced (e.g. live E-utilities fetch vs.
    the committed offline seed), so a reader knows whether the IDs map to real article
    text. Sources are sorted by ``(connector, external_id)`` for a stable, diff-friendly
    file regardless of ingest order.
    """
    generated_at = generated_at or dt.datetime.now(dt.UTC)
    sources = sorted(report.sources, key=lambda source: (source.connector, source.external_id))
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "provenance": provenance,
        "trust_tier": trust_tier.value,
        "embedding": {
            "provider": report.embedding_provider,
            "model": report.embedding_model,
            "dimension": report.embedding_dimension,
        },
        "totals": {
            "sources": len(sources),
            "documents": report.total_documents,
            "chunks": report.total_chunks,
        },
        "sources": [
            {
                "connector": source.connector,
                "external_id": source.external_id,
                "title": source.title,
                "documents": source.documents,
                "chunks": source.chunks,
            }
            for source in sources
        ],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write ``manifest`` as pretty-printed JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
