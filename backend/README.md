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
│   ├── db/                # declarative base + async session
│   ├── corpus/            # corpus schema (source → document → chunk)
│   └── evaluation/        # Phase 1 grounded-vs-baseline harness
├── alembic/               # database migrations
└── tests/                 # pytest suite
```
