"""Command-line entry point for corpus ingestion.

Run a connector over a set of IDs (or committed offline fixtures), chunk + embed the
results, optionally persist them to Postgres, and optionally write the corpus manifest::

    # Live: fetch real PMIDs and store them (needs network + a running database)
    python -m aletheia.corpus.cli ingest --connector pubmed --ids 31452104,33301246 \\
        --manifest data/corpus/manifest.json

    # Offline: rebuild the committed seed manifest from fixtures, no DB, no network
    python -m aletheia.corpus.cli ingest --connector pmc \\
        --fixtures-dir data/corpus/seeds/pmc --embedder fake --no-persist \\
        --manifest data/corpus/manifest.json

The offline path is what regenerates the committed manifest and runs in CI; the live
path is what builds the real frozen corpus the benchmarks cite (ADR-0006).
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from aletheia.config import get_settings
from aletheia.corpus.chunking import DEFAULT_CHUNK_CHARS, DEFAULT_CHUNK_OVERLAP, ChunkConfig
from aletheia.corpus.connectors import CONNECTORS, FetchedSource, SourceConnector
from aletheia.corpus.ingest import IngestReport, SourceReport, assemble_source, ingest
from aletheia.corpus.manifest import build_manifest, write_manifest
from aletheia.corpus.models import EMBEDDING_DIM
from aletheia.db.session import get_sessionmaker
from aletheia.embeddings import build_embedder
from aletheia.embeddings.base import Embedder
from aletheia.embeddings.fake import FakeEmbedder
from aletheia.embeddings.local import LocalEmbedder


def _build_embedder(choice: str | None) -> Embedder:
    """Resolve the embedder by name, falling back to the configured default."""
    if choice is None:
        return build_embedder()
    if choice == "fake":
        return FakeEmbedder(dimension=EMBEDDING_DIM)
    if choice == "local":
        return LocalEmbedder(dimension=EMBEDDING_DIM)
    if choice == "gemini":
        # Force the Gemini provider regardless of EMBEDDING_PROVIDER, reusing the
        # factory's key validation and model defaulting.
        settings = get_settings().model_copy(update={"embedding_provider": "gemini"})
        return build_embedder(settings)
    raise ValueError(f"unknown embedder: {choice}")


def _resolve_ids(args: argparse.Namespace) -> list[str]:
    ids: list[str] = list(args.id or [])
    if args.ids:
        ids.extend(part.strip() for part in args.ids.split(",") if part.strip())
    if args.ids_file:
        for line in Path(args.ids_file).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                ids.append(stripped)
    return ids


def _parse_fixtures(connector: SourceConnector, fixtures_dir: Path) -> list[FetchedSource]:
    sources: list[FetchedSource] = []
    for path in sorted(fixtures_dir.glob("*.xml")):
        sources.extend(connector.parse(path.read_text(encoding="utf-8")))
    return sources


def _parse_corpus_file(connector: SourceConnector, corpus_file: Path) -> list[FetchedSource]:
    return connector.parse(corpus_file.read_text(encoding="utf-8"))


async def _gather_sources(
    connector: SourceConnector, args: argparse.Namespace
) -> list[FetchedSource]:
    if args.corpus_file:
        sources = _parse_corpus_file(connector, Path(args.corpus_file))
    elif args.fixtures_dir:
        sources = _parse_fixtures(connector, Path(args.fixtures_dir))
    else:
        ids = _resolve_ids(args)
        if not ids:
            raise SystemExit(
                "no sources given: pass --id/--ids/--ids-file, --fixtures-dir, or --corpus-file"
            )
        sources = await connector.fetch(ids)
    if args.limit is not None:
        sources = sources[: args.limit]
    return sources


async def _assemble_only(
    sources: Sequence[FetchedSource], *, embedder: Embedder, chunking: ChunkConfig
) -> IngestReport:
    """Build the corpus graph in memory and report it, without touching the database."""
    report = IngestReport(
        embedding_provider=embedder.provider,
        embedding_model=embedder.model,
        embedding_dimension=embedder.dimension,
    )
    for fetched in sources:
        source = await assemble_source(fetched, embedder=embedder, chunking=chunking)
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


async def _run(args: argparse.Namespace) -> int:
    connector = CONNECTORS[args.connector]()
    embedder = _build_embedder(args.embedder)
    chunking = ChunkConfig(max_chars=args.max_chars, overlap=args.overlap)
    sources = await _gather_sources(connector, args)
    if not sources:
        print("no sources parsed; nothing to ingest")
        return 0

    if args.no_persist:
        report = await _assemble_only(sources, embedder=embedder, chunking=chunking)
    else:
        async with get_sessionmaker()() as session:
            report = await ingest(
                session, sources, embedder=embedder, chunking=chunking, replace=args.replace
            )

    _print_report(report)
    if args.manifest:
        provenance = _provenance(args)
        manifest = build_manifest(report, provenance=provenance)
        write_manifest(Path(args.manifest), manifest)
        print(f"\nwrote manifest → {args.manifest}")
    return 0


def _provenance(args: argparse.Namespace) -> str:
    """The manifest provenance note describing where this run's sources came from."""
    if args.provenance:
        return str(args.provenance)
    if args.corpus_file:
        return f"ingested from corpus file {Path(args.corpus_file).name}"
    if args.fixtures_dir:
        return "offline seed (parsed from committed fixtures)"
    return "live E-utilities fetch"


def _print_report(report: IngestReport) -> None:
    print(
        f"embedder: {report.embedding_provider}/{report.embedding_model} "
        f"({report.embedding_dimension}-dim)"
    )
    for source in report.sources:
        print(
            f"  [{source.status:>8}] {source.connector}:{source.external_id} "
            f"— {source.documents} docs, {source.chunks} chunks — {source.title[:60]}"
        )
    print(
        f"totals: {len(report.sources)} sources, "
        f"{report.total_documents} documents, {report.total_chunks} chunks"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aletheia.corpus.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="ingest sources into the corpus")
    ingest_parser.add_argument("--connector", required=True, choices=sorted(CONNECTORS))
    ingest_parser.add_argument("--id", action="append", help="a single external ID (repeatable)")
    ingest_parser.add_argument("--ids", help="comma-separated external IDs")
    ingest_parser.add_argument("--ids-file", help="file with one external ID per line")
    ingest_parser.add_argument(
        "--fixtures-dir", help="parse *.xml here offline instead of fetching from the network"
    )
    ingest_parser.add_argument(
        "--corpus-file",
        help="parse one bulk corpus file offline (e.g. the SciFact corpus.jsonl)",
    )
    ingest_parser.add_argument(
        "--limit", type=int, help="ingest at most this many sources (applied after parsing)"
    )
    ingest_parser.add_argument(
        "--embedder", choices=["local", "gemini", "fake"], help="override the configured embedder"
    )
    ingest_parser.add_argument(
        "--no-persist", action="store_true", help="assemble in memory only; do not write to the DB"
    )
    ingest_parser.add_argument(
        "--replace", action="store_true", help="re-ingest sources already present"
    )
    ingest_parser.add_argument("--manifest", help="write the corpus manifest to this path")
    ingest_parser.add_argument("--provenance", help="override the manifest provenance note")
    ingest_parser.add_argument("--max-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    ingest_parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
