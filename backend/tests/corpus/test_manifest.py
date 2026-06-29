"""Tests for the corpus manifest: building from a report, and seed reproducibility."""

from __future__ import annotations

import datetime as dt
import json

from aletheia.corpus.ingest import IngestReport, SourceReport
from aletheia.corpus.manifest import MANIFEST_SCHEMA_VERSION, build_manifest
from aletheia.corpus.seed import MANIFEST_PATH, build_seed_manifest


def _report() -> IngestReport:
    return IngestReport(
        embedding_provider="local",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dimension=384,
        sources=[
            SourceReport("pubmed", "40000002", "Second", documents=2, chunks=3, status="created"),
            SourceReport("pubmed", "40000001", "First", documents=1, chunks=2, status="created"),
        ],
    )


def test_manifest_records_embedding_and_totals() -> None:
    manifest = build_manifest(
        _report(), provenance="unit test", generated_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    )

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["provenance"] == "unit test"
    assert manifest["trust_tier"] == "curated_corpus"
    assert manifest["embedding"] == {
        "provider": "local",
        "model": "BAAI/bge-small-en-v1.5",
        "dimension": 384,
    }
    assert manifest["totals"] == {"sources": 2, "documents": 3, "chunks": 5}
    assert manifest["generated_at"] == "2026-01-01T00:00:00+00:00"


def test_manifest_sources_are_sorted_for_stable_diffs() -> None:
    manifest = build_manifest(_report(), provenance="unit test")
    ids = [(source["connector"], source["external_id"]) for source in manifest["sources"]]
    assert ids == sorted(ids)


async def test_committed_seed_manifest_is_in_sync_with_fixtures() -> None:
    """Regenerating the seed manifest must match the committed file (apart from its date).

    This is the reproducibility guard: change a fixture without regenerating the manifest
    and CI fails here.
    """
    committed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    regenerated = await build_seed_manifest()

    committed.pop("generated_at")
    regenerated.pop("generated_at")
    assert regenerated == committed
