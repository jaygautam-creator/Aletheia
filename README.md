<div align="center">

# Aletheia

**An evidence-grounded, multi-agent verification framework — with a rigorous
evaluation harness — that improves the reliability of LLM answers by grounding
every claim in real evidence and surfacing disagreement instead of hiding it.**

[![CI](https://github.com/jaygautam-creator/Aletheia/actions/workflows/ci.yml/badge.svg)](https://github.com/jaygautam-creator/Aletheia/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](backend/pyproject.toml)
[![Next.js](https://img.shields.io/badge/Next.js-App%20Router-black.svg)](frontend)

*Aletheia (ἀλήθεια): ancient Greek for "truth" — literally "unconcealment", the
revealing of what was hidden.*

</div>

---

## The problem

Large Language Models confidently produce **hallucinations** — fluent answers
that are factually wrong, or that cite sources which do not actually support the
claim. A model sounds equally confident whether it is right or completely wrong,
so users get **no reliable signal for which answers to trust**. In medicine, law,
finance, and education, acting on an unverified wrong answer causes real harm.

Single models cannot reliably catch their own mistakes, and naive multi-agent
setups suffer from **false agreement** — agents reinforce each other's errors
instead of detecting them.

## The approach

Aletheia runs a pipeline of specialized agents that produce **and verify** an
answer, where **every verdict must quote the exact source span that justifies
it**. Grounding verdicts in evidence — not opinion — is what defeats false
agreement.

```
query → guardrail → Generator → Retriever → Verifier(s) → Aggregator
                    (answer +    (hybrid     (Supported /   (final answer +
                     claims)      search)     Contradicted / confidence +
                                              Unverifiable,  disagreements)
                                              with quoted
                                              evidence span)
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design and diagrams.

## The differentiator

The **evaluation harness is the centerpiece**. It runs the system repeatedly over
public hallucination benchmarks and measures — against a single-LLM baseline —
verification accuracy, hallucination-catch rate, false-agreement rate, latency
(p50/p95/p99), and per-query cost. The headline deliverable is a results table
proving the grounded multi-agent approach catches measurably more errors than a
single model. Methodology lives in [`EVALUATION.md`](EVALUATION.md).

## Benchmark results

> _Pending Phase 3._ This section will hold the headline comparison table the
> moment the harness produces numbers.

| System | Verification accuracy | Hallucination-catch rate | False-agreement rate | Latency (p50/p95/p99) | Cost/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | — | — | — | — | — |
| **Aletheia** | — | — | — | — | — |

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js (App Router, TypeScript) |
| Backend | FastAPI (async Python) |
| Agent orchestration | LangGraph (+ LangChain) |
| Vector store | PostgreSQL + pgvector |
| LLM runtime | Gemini / Groq free tiers (provider-agnostic, via env vars) |
| Cache / queue | Redis |
| Observability | Prometheus + Grafana, OpenTelemetry-style tracing |
| Packaging & deploy | Docker, docker-compose, Kubernetes |
| CI/CD | GitHub Actions |
| Python tooling | uv · ruff · mypy · pytest |

Every component has a genuinely free option; runtime LLM keys are user-supplied.

## Getting started

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) (with Compose),
and for local development: [uv](https://docs.astral.sh/uv/) and Node.js 20+.

```bash
# 1. Clone
git clone https://github.com/jaygautam-creator/Aletheia.git
cd Aletheia

# 2. Configure (no real keys are needed until Phase 1)
cp .env.example .env

# 3a. Run the whole stack in containers
docker compose up --build
# Backend  → http://localhost:8000  (health: http://localhost:8000/health)
# Frontend → http://localhost:3000

# 3b. …or develop locally
make install   # backend (uv) + frontend (npm) dependencies
make dev       # run backend and frontend dev servers
make test      # run the test suites
```

Run `make help` to see all available commands.

## Project status

Built phase-by-phase; progress is tracked in [`ROADMAP.md`](ROADMAP.md) and
narrated in plain language in [`PROGRESS_LOG.md`](PROGRESS_LOG.md).

- ✅ **Phase 0 — Foundation & Governance** *(current)*: repo, governance docs,
  backend/frontend/infra skeleton, containers, and CI.
- ⬜ Phase 1 — Prove the thesis: minimal Generator + grounded Verifier.
- ⬜ Phase 2 — Retrieval & grounding (pgvector, hybrid search, guardrails).
- ⬜ Phase 3 — The evaluation harness (centerpiece).
- ⬜ Phase 4 — Real-time frontend.
- ⬜ Phase 5 — Production engineering.
- ⬜ Phase 6 — Paper & polish.

## Documentation

| Document | Purpose |
| --- | --- |
| [`PROJECT_CHARTER.md`](PROJECT_CHARTER.md) | Authoritative definition, scope, success criteria |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System design, data flow, and decisions |
| [`EVALUATION.md`](EVALUATION.md) | Methodology and benchmark results |
| [`ROADMAP.md`](ROADMAP.md) | Phase-by-phase plan with progress |
| [`ANTI_DRIFT.md`](ANTI_DRIFT.md) | Scope guardrails |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development setup and conventions |

## License

[MIT](LICENSE) © 2026 Jay Gautam
