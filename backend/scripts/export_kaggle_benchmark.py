"""One-off export: freeze a stratified SciFact sample + its retrieved evidence to JSONL
for running the grounded-vs-baseline comparison outside this repo (e.g. a Kaggle
notebook, where `kaggle_benchmarks` gives access to models like
google/gemini-3.1-flash-lite-preview that have no external API key).

Retrieval is run once here, against the same live corpus/embedder phase3.py uses, so
the exported evidence is identical to what Groq/Nemotron runs saw — the only variable
in the downstream comparison is the verifying model.

Usage: uv --directory backend run python scripts/export_kaggle_benchmark.py \
    --claims data/scifact/claims_dev.jsonl --sample 100 --seed 7 --out runs/kaggle_export.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json

from aletheia.corpus.retrieval import Retriever, format_evidence
from aletheia.db.session import get_sessionmaker
from aletheia.embeddings import build_embedder
from aletheia.evaluation.benchmark import load_scifact_claims, stratified_sample


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", required=True)
    parser.add_argument("--sample", type=int, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    items = stratified_sample(load_scifact_claims(args.claims), args.sample, seed=args.seed)
    embedder = build_embedder()

    async with get_sessionmaker()() as session:
        retriever = Retriever(session, embedder=embedder, connector="scifact")
        # Offline one-shot export: a blocking write is correct here, and the row
        # is only assembled after the awaited retrieval above.
        with open(args.out, "w") as f:  # noqa: ASYNC230
            for item in items:
                sources = list(await retriever.search(item.claim))
                evidence = format_evidence(sources)
                f.write(
                    json.dumps(
                        {
                            "id": item.id,
                            "claim": item.claim,
                            "gold": item.gold.value,
                            "evidence": evidence,
                        }
                    )
                    + "\n"
                )

    print(f"wrote {len(items)} items -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
