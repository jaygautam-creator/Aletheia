"""Seeded FEVER corpus-slice builder (ADR-0011, plan 0002 E2).

FEVER's full wiki dump is ~5.4M pages — not free-tier-ingestable, and out of step with
this project's "benchmark on a fixed, sized corpus" rule (ADR-0006). This module builds
a deterministic slice sized like SciFact's (~5K documents) instead: every page cited by
a sampled claim set's gold evidence, plus seeded random distractor pages up to a target
size. Given the same ``(claims, sample_size, seed, corpus_target)``, the slice is always
identical, so a run is reproducible from its parameters alone.

The selection logic (:func:`build_corpus_slice`) is pure — it only ever sees ids, never
touches disk, and is exercised entirely offline in tests. The dump-reading half
(:func:`index_wiki_pages`, :func:`write_corpus_slice_file`) is the thin I/O edge that
turns a set of chosen ids into an ingestable ``fever`` connector JSONL file; it is still
unit-tested, against small fabricated shard files, never the real multi-gigabyte dump.
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from aletheia.evaluation.benchmark import BenchmarkItem, load_fever_claims, stratified_sample


@dataclass(frozen=True, slots=True)
class CorpusSlice:
    """A seeded claim sample plus the ordered set of Wikipedia pages it needs ingested."""

    claims: tuple[BenchmarkItem, ...]
    evidence_page_ids: tuple[str, ...]
    distractor_page_ids: tuple[str, ...]

    @property
    def page_ids(self) -> tuple[str, ...]:
        """Every page the ingest CLI should pull from the dump, evidence pages first."""
        return self.evidence_page_ids + self.distractor_page_ids


@dataclass(frozen=True, slots=True)
class SliceManifest:
    """Slice provenance recorded alongside the ingested corpus (ADR-0011's honesty note)."""

    dataset: str
    sample_size: int
    seed: int
    corpus_target: int
    claim_count: int
    evidence_page_count: int
    distractor_page_count: int

    @property
    def total_page_count(self) -> int:
        return self.evidence_page_count + self.distractor_page_count

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset": self.dataset,
            "sample_size": self.sample_size,
            "seed": self.seed,
            "corpus_target": self.corpus_target,
            "claim_count": self.claim_count,
            "evidence_page_count": self.evidence_page_count,
            "distractor_page_count": self.distractor_page_count,
            "total_page_count": self.total_page_count,
            "caveat": (
                "closed-corpus slice built from the sampled claims' own evidence pages "
                "plus seeded distractors — retrieval is easier than the full FEVER "
                "Wikipedia dump; not comparable to FEVER shared-task systems (ADR-0011)"
            ),
        }


def build_corpus_slice(
    claims: Sequence[BenchmarkItem],
    available_page_ids: Sequence[str],
    *,
    sample_size: int,
    seed: int,
    corpus_target: int,
) -> CorpusSlice:
    """Draw the seeded claim sample and the corpus slice it needs.

    ``available_page_ids`` is every page id the dump actually has (order matters only in
    that it is stable input — the distractor draw is reseeded, not order-dependent).
    Evidence pages absent from ``available_page_ids`` are silently excluded from the
    distractor pool consideration but still recorded as wanted; the caller's dump-reader
    simply won't find them, which is a data problem, not a slicing one.
    """
    sampled = stratified_sample(claims, sample_size, seed=seed)

    evidence_ids: list[str] = []
    seen: set[str] = set()
    for item in sampled:
        for page_id in item.cited_doc_ids:
            if page_id not in seen:
                seen.add(page_id)
                evidence_ids.append(page_id)

    remaining = max(0, corpus_target - len(evidence_ids))
    pool = [page_id for page_id in available_page_ids if page_id not in seen]
    rng = random.Random(seed)
    distractors = rng.sample(pool, min(remaining, len(pool)))

    return CorpusSlice(
        claims=tuple(sampled),
        evidence_page_ids=tuple(evidence_ids),
        distractor_page_ids=tuple(distractors),
    )


def build_slice_manifest(
    slice_: CorpusSlice, *, seed: int, sample_size: int, corpus_target: int
) -> SliceManifest:
    return SliceManifest(
        dataset="fever",
        sample_size=sample_size,
        seed=seed,
        corpus_target=corpus_target,
        claim_count=len(slice_.claims),
        evidence_page_count=len(slice_.evidence_page_ids),
        distractor_page_count=len(slice_.distractor_page_ids),
    )


def index_wiki_pages(wiki_pages_dir: Path) -> dict[str, Path]:
    """Scan every ``*.jsonl`` shard in ``wiki_pages_dir`` once, mapping page id -> shard.

    The dump ships one page per line across many sharded files; this builds the id ->
    file lookup :func:`write_corpus_slice_file` needs, without holding page bodies in
    memory. The first shard to define an id wins (FEVER's dump does not repeat ids).
    """
    index: dict[str, Path] = {}
    for shard in sorted(wiki_pages_dir.glob("*.jsonl")):
        for line in shard.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            page_id = str(json.loads(line)["id"])
            index.setdefault(page_id, shard)
    return index


def write_corpus_slice_file(
    page_ids: Iterable[str], index: Mapping[str, Path], output_path: Path
) -> int:
    """Write the dump lines for ``page_ids`` to ``output_path``, ready for connector ingest.

    Returns the count of ids actually found and written (fewer than requested if a
    cited page has since been removed from a re-downloaded dump — not raised on, since
    that is a data-freshness fact the caller's manifest should record, not a crash).
    """
    wanted = set(page_ids)
    by_shard: dict[Path, set[str]] = {}
    for page_id in wanted:
        shard = index.get(page_id)
        if shard is not None:
            by_shard.setdefault(shard, set()).add(page_id)

    written = 0
    with output_path.open("w", encoding="utf-8") as out:
        for shard, ids in by_shard.items():
            for line in shard.read_text("utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if str(record["id"]) in ids:
                    out.write(line + "\n")
                    written += 1
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aletheia.evaluation.fever_slice", description=__doc__)
    parser.add_argument("--claims", required=True, help="path to a FEVER claims JSONL file")
    parser.add_argument("--wiki-pages-dir", required=True, help="directory of dump *.jsonl shards")
    parser.add_argument("--sample", type=int, required=True, help="stratified claim sample size")
    parser.add_argument("--seed", type=int, default=7, help="drives the sample and distractor draw")
    parser.add_argument(
        "--corpus-target",
        type=int,
        default=5000,
        help="total pages in the slice (evidence + distractor)",
    )
    parser.add_argument(
        "--output", required=True, help="path to write the sliced fever corpus JSONL"
    )
    parser.add_argument("--manifest-out", help="path to write the slice manifest JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    claims = load_fever_claims(args.claims)
    index = index_wiki_pages(Path(args.wiki_pages_dir))
    slice_ = build_corpus_slice(
        claims,
        list(index),
        sample_size=args.sample,
        seed=args.seed,
        corpus_target=args.corpus_target,
    )
    written = write_corpus_slice_file(slice_.page_ids, index, Path(args.output))
    manifest = build_slice_manifest(
        slice_, seed=args.seed, sample_size=args.sample, corpus_target=args.corpus_target
    )
    print(f"Wrote {written}/{len(slice_.page_ids)} pages to {args.output}")
    if args.manifest_out:
        Path(args.manifest_out).write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", "utf-8")
        print(f"Slice manifest: {args.manifest_out}")


if __name__ == "__main__":
    main()
