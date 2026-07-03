# Contributing

Aletheia is primarily a solo capstone authored by Jay Gautam, but it is built to
professional standards and welcomes well-scoped issues and pull requests.

## Ground rules

- **Free-tier only.** Do not introduce any dependency, service, or model that
  lacks a genuinely free option.
- **Stay in scope.** Read `ANTI_DRIFT.md` first. Changes must serve
  evidence-grounded verification, the evaluation harness, or reliable free-tier
  operation.
- **Production quality.** Match the surrounding code's style, naming, and test
  coverage. No placeholder code or stray TODOs.

## Development setup

```bash
# Prerequisites: uv, Node.js 20+, Docker.
make install      # install backend (uv) and frontend (npm) dependencies
make dev          # run backend + frontend dev servers together (Ctrl+C stops both)
make test         # run backend and frontend tests
make lint         # ruff + eslint
make type-check   # mypy + tsc
make up           # run the full stack via docker compose
```

Runtime configuration lives in the root `.env` (copy `.env.example`; never
committed). Note the quirk: `backend/.env` is a **symlink** to the root `.env`,
because the backend resolves its config relative to the `backend/` directory —
edit the root file, not a copy.

See `backend/README.md` and `frontend/README.md` for service-specific commands,
and run `make help` for the full command list.

### Observability (optional)

The backend exposes Prometheus metrics at `/metrics` (request counts/durations and
per-pipeline-stage histograms). To watch them locally:

```bash
docker compose --profile obs up   # Prometheus on :9090, Grafana on :3001
```

Grafana (anonymous admin, local only) auto-provisions the committed
"Aletheia — service overview" dashboard from `infra/observability/`. Set
`LOG_FORMAT=json` for structured one-object-per-line logs tagged with each
request's `X-Request-ID`.

## Branching & commits

- Branch from `main` using a descriptive prefix: `feat/…`, `fix/…`, `docs/…`,
  `chore/…`, `ci/…`, `refactor/…`, `test/…`.
- Use [Conventional Commits](https://www.conventionalcommits.org/): a clear type,
  scope, and an imperative description of *what* and *why*.
- Open a pull request into `main`. CI (lint, type-check, tests) must pass.

## Code style

- **Python:** formatted and linted with `ruff`, type-checked with `mypy`, tested
  with `pytest`. 4-space indentation, type hints required on public functions.
- **TypeScript/React:** linted with ESLint, type-checked with `tsc`. App Router
  conventions; 2-space indentation.
- Keep functions small and named for intent. Comments explain *why*, not *what*.

## Tests

Every behavioral change ships with a test. Bug fixes start with a failing test
that the fix turns green. The evaluation harness has its own reproducibility
requirements documented in `EVALUATION.md`.
