"""The committed offline seed corpus and its manifest.

The repository ships a tiny, *synthetic* seed corpus under ``data/corpus/seeds`` —
schema-faithful PubMed/PMC fixtures with invented content and IDs. It exists so the
ingestion pipeline and manifest format are exercised end-to-end with no network and no
model download, and so CI can assert the manifest stays in sync with the fixtures.

It is **not** the citable frozen corpus the benchmarks run on (ADR-0006): that is built
by running the live CLI over real PubMed/PMC IDs with the real embedder, which
regenerates ``data/corpus/manifest.json`` with real provenance. This module is the
offline counterpart that keeps the committed manifest honest and reproducible.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from pathlib import Path
from typing import Any

from aletheia.corpus.connectors import CONNECTORS
from aletheia.corpus.ingest import IngestReport, SourceReport, assemble_source
from aletheia.corpus.manifest import build_manifest, write_manifest
from aletheia.corpus.models import EMBEDDING_DIM
from aletheia.embeddings.fake import FakeEmbedder

#: ``…/backend`` — three parents up from this module (corpus → aletheia → src → backend).
BACKEND_DIR = Path(__file__).resolve().parents[3]
SEEDS_DIR = BACKEND_DIR / "data" / "corpus" / "seeds"
MANIFEST_PATH = BACKEND_DIR / "data" / "corpus" / "manifest.json"

#: Provenance recorded in the seed manifest — deliberately explicit that it is synthetic.
SEED_PROVENANCE = (
    "offline seed: synthetic, schema-faithful PubMed/PMC fixtures embedded with the "
    "deterministic fake embedder. Not the citable frozen corpus — regenerate from live "
    "E-utilities IDs with the real embedder to build that."
)

#: Which connector parses which fixtures subdirectory, in a stable order.
SEED_SOURCES: tuple[tuple[str, str], ...] = (
    ("pubmed", "pubmed"),
    ("pmc", "pmc"),
)


async def build_seed_report() -> IngestReport:
    """Parse and assemble the whole seed corpus in memory (no DB, no network)."""
    embedder = FakeEmbedder(dimension=EMBEDDING_DIM)
    report = IngestReport(
        embedding_provider=embedder.provider,
        embedding_model=embedder.model,
        embedding_dimension=embedder.dimension,
    )
    for connector_name, subdir in SEED_SOURCES:
        connector = CONNECTORS[connector_name]()
        for path in sorted((SEEDS_DIR / subdir).glob("*.xml")):
            for fetched in connector.parse(path.read_text(encoding="utf-8")):
                source = await assemble_source(fetched, embedder=embedder)
                report.sources.append(
                    SourceReport(
                        connector=source.connector,
                        external_id=source.external_id,
                        title=source.title,
                        documents=len(source.documents),
                        chunks=sum(len(document.chunks) for document in source.documents),
                        status="created",
                    )
                )
    return report


async def build_seed_manifest(*, generated_at: dt.datetime | None = None) -> dict[str, Any]:
    """Build the seed manifest document (the source of truth for the committed file)."""
    report = await build_seed_report()
    return build_manifest(report, provenance=SEED_PROVENANCE, generated_at=generated_at)


def main() -> int:
    manifest = asyncio.run(build_seed_manifest())
    write_manifest(MANIFEST_PATH, manifest)
    totals = manifest["totals"]
    print(
        f"wrote seed manifest → {MANIFEST_PATH.relative_to(BACKEND_DIR)} "
        f"({totals['sources']} sources, {totals['documents']} documents, "
        f"{totals['chunks']} chunks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
