# Aletheia — Backend

Async FastAPI service that orchestrates the multi-agent verification pipeline.
Phase 0 exposes service metadata and a health endpoint; the agent graph,
retrieval, and evaluation hooks arrive in later phases.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Common commands

```bash
uv sync                 # create the virtualenv and install all dependencies
uv run uvicorn aletheia.main:app --reload   # run the dev server on :8000
uv run pytest           # run the test suite
uv run ruff check .     # lint
uv run ruff format .    # format
uv run mypy src         # type-check
```

## Database & migrations

The corpus and hybrid retrieval are backed by PostgreSQL + pgvector. Schema changes
are managed with Alembic; the connection string is read from `DATABASE_URL` (see
`.env.example`), defaulting to the local docker-compose service.

```bash
docker compose up -d postgres        # start Postgres + pgvector locally
uv run alembic upgrade head          # apply migrations  (make db-upgrade)
uv run alembic downgrade -1          # roll back one     (make db-downgrade)
uv run alembic revision --autogenerate -m "describe change"   # (make db-revision)
```

## Corpus ingestion

The curated corpus is built from PubMed/PMC open-access literature by connectors that
fetch a source, normalise it, chunk it, embed the chunks, and store them tagged
`CURATED_CORPUS` (ADR-0003). Ingestion is idempotent — re-running skips sources already
present (use `--replace` to rebuild one).

```bash
# Live: fetch real PMIDs into a running database, then write the manifest
uv run python -m aletheia.corpus.cli ingest \
    --connector pubmed --ids 31452104,33301246 --manifest data/corpus/manifest.json

# PMC open-access full text
uv run python -m aletheia.corpus.cli ingest --connector pmc --ids 7327471
```

Only the live fetch needs the network; parsing, chunking, and assembly are exercised
offline. `NCBI_EMAIL`/`NCBI_API_KEY` (optional) identify the client to NCBI and lift the
request-rate limit.

### The corpus manifest

For benchmark numbers to be reproducible the corpus must be pinned (ADR-0006), so an
ingest can emit `data/corpus/manifest.json` — the embedding model/width, trust tier,
ingested source IDs, and document/chunk counts.

The repository ships a tiny **synthetic** seed corpus under `data/corpus/seeds/` plus a
committed manifest generated from it. It exists to exercise the pipeline and manifest
format with no network and no model download; it is *not* the citable frozen corpus (its
provenance field says so). Regenerate it after editing a fixture — CI asserts the two
stay in sync:

```bash
uv run python -m aletheia.corpus.seed     # make corpus-seed-manifest
```

## Hybrid retrieval

`aletheia.corpus.retrieval.Retriever` searches the chunk corpus two ways from the same
table — vector cosine similarity (pgvector, the HNSW index) and full-text keyword match
(the generated `tsvector`, the GIN index) — and merges the two rankings with Reciprocal
Rank Fusion. RRF compares only ranks, so the incomparable score scales never have to be
reconciled, and a chunk both branches like outranks one a single branch ranks highly.

Each hit is a `RetrievedEvidence` carrying its source's trust tier, so downstream code
never handles untiered evidence (ADR-0003). The fusion math and result assembly are pure
and unit-tested; the two SQL branches are covered by the Postgres integration tests. Pool
sizes and the RRF constant are tunable via `RETRIEVAL_TOP_K`, `RETRIEVAL_CANDIDATES`, and
`RRF_K`.

The Retriever is wired into the verification graph as a node ahead of the Generator: when
`/verify` is called without `evidence`, the node searches the corpus and grounds the
verdicts in what it finds, returning the sources as `citations`. Supplying `evidence`
keeps the Phase 1 behaviour (the node is a pass-through) — the verdict contract is
unchanged either way.

## Endpoints

| Method | Path      | Description            |
| ------ | --------- | ---------------------- |
| GET    | `/`       | Service metadata       |
| GET    | `/health` | Liveness/health check  |
| GET    | `/docs`   | Interactive OpenAPI UI |

## Layout

```
backend/
├── src/aletheia/
│   ├── __init__.py        # package version
│   ├── main.py            # application factory + entrypoint
│   ├── config.py          # environment-driven settings
│   ├── api/routes/        # HTTP route modules
│   ├── agents/            # LangGraph pipeline + verdict contracts
│   ├── llm/               # provider-agnostic LLM client
│   ├── embeddings/        # provider-agnostic embedder (local ONNX default)
│   ├── db/                # declarative base + async session
│   ├── corpus/            # schema, connectors, chunking, ingestion, retrieval, manifest, CLI
│   └── evaluation/        # Phase 1 grounded-vs-baseline harness
├── alembic/               # database migrations
├── data/corpus/           # seed fixtures + committed corpus manifest
└── tests/                 # pytest suite
```
