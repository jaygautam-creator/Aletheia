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
│   └── api/routes/        # HTTP route modules
└── tests/                 # pytest suite
```
