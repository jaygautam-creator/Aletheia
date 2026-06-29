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

### The SciFact benchmark corpus

Phase 3 grounds the SciFact benchmark in the corpus, so the corpus is grown to cover it.
SciFact ships its evidence as a single `corpus.jsonl` of abstracts (download from the
[SciFact release](https://github.com/allenai/scifact)); the `scifact` connector parses
that bulk file rather than fetching by id:

```bash
uv run python -m aletheia.corpus.cli ingest \
    --connector scifact --corpus-file data/scifact/corpus.jsonl \
    --manifest data/corpus/manifest.json        # --limit N caps how many abstracts to ingest
```

Embedding runs through the local model (free, offline), so ingesting the whole corpus
needs no API budget. SciFact is CC BY-NC 2.0; that licence is recorded on every source.

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

## Guardrails & disclaimer

Grounding is enforced in the Verifier (no verdict may affirm a claim without quoting
evidence). A final **guardrail node** (`aletheia.agents.guardrails`) runs last and does
the complementary, **non-mutating** job: it reads the assembled result and attaches a
`safety` advisory — `info` when every claim is grounded as Supported, `caution` when a
claim could not be grounded, `high_caution` when the evidence contradicts a claim — plus
the standing medical-advice disclaimer. It never edits a verdict or the answer, so the
verdict contract is untouched; `/verify` simply carries `safety` alongside `citations`,
and the disclaimer is also surfaced on the service metadata at `GET /`.

## Tests

The default suite is fully offline — `uv run pytest` excludes everything marked
`integration`, so it needs no database, no network, and no model download. The
integration tests are opt-in:

```bash
# Database-backed (ingestion + hybrid retrieval) against a running pgvector:
docker compose up -d postgres
uv run pytest -m "integration and database"

# Everything integration, including the one-off local-model download:
uv run pytest -m integration
```

CI provisions an ephemeral PostgreSQL + pgvector service and runs the
`integration and database` tests on every change, so the two SQL branches are
exercised for real — the model-download test stays out of CI by design.

## Endpoints

| Method | Path      | Description                                  |
| ------ | --------- | -------------------------------------------- |
| GET    | `/`       | Service metadata (incl. disclaimer)          |
| GET    | `/health` | Liveness/health check                        |
| POST   | `/verify` | Verify claims against evidence (or corpus)   |
| GET    | `/docs`   | Interactive OpenAPI UI                       |

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
