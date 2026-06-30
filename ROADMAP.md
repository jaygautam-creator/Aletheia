# Roadmap

Phase-by-phase plan. Each phase ends with **tests passing, docs updated, and a
commit + push**. At the start of each phase, a detailed task breakdown is
proposed and approved before work begins. Checkboxes are the single source of
truth for "what's done".

Legend: `[ ]` not started · `[~]` in progress · `[x]` complete

---

## Phase 0 — Foundation & Governance

- [x] Repository initialized with author-only git identity
- [x] Public GitHub repository created
- [x] Repo hygiene: `.gitignore`, `.gitattributes`, `.editorconfig`, `LICENSE` (MIT), `.env.example`
- [x] Governance docs: `PROJECT_CHARTER.md`, `ANTI_DRIFT.md`, `ROADMAP.md`, `PROGRESS_LOG.md`, `ARCHITECTURE.md`, `EVALUATION.md`, `CONTRIBUTING.md`
- [x] Recruiter-grade `README.md`
- [x] Backend skeleton: FastAPI (async) with `/health`, managed by uv, with ruff + mypy + pytest
- [x] Frontend skeleton: Next.js (App Router, TypeScript) landing page
- [x] Infra baseline: Dockerfiles, `docker-compose.yml` (backend, frontend, postgres+pgvector, redis), `k8s/` placeholder
- [x] Developer tooling: `Makefile`, pre-commit config
- [x] CI: GitHub Actions running lint + type-check + tests for backend and frontend
- [x] Phase 0 merged to `main` via pull request

## Phase 1 — Prove the hard part early (de-risk the thesis)

- [x] Minimal LangGraph pipeline: Generator + one grounded Verifier
- [x] Provider-agnostic LLM client (Gemini / Groq) behind a clean interface
- [x] A small, curated dataset with deliberately planted unsupported claims
- [x] Demonstrate the Verifier catching an unsupported claim a single model misses
- [x] First measurable comparison: multi-agent vs single-model on the mini set
- [x] Tests for graph nodes and the verification verdict contract

## Phase 2 — Retrieval & grounding

- [x] PostgreSQL + pgvector schema and migrations
- [x] Source corpus ingestion pipeline (chunking, embeddings)
- [x] Hybrid retrieval (semantic + keyword) with ranking
- [x] Claim-level grounding: every verdict cites an exact source span
- [~] Guardrail layer — *delivered:* a non-mutating output advisory
  (info / caution / high-caution) plus a standing medical-advice disclaimer,
  on top of the Verifier's hard grounding rule. *Deferred:* input-side
  prompt-injection screening and unsafe-content filtering (tracked for the
  Phase 5 hardening pass)
- [x] Tests for retrieval relevance and span-grounding correctness

## Phase 3 — The evaluation harness (centerpiece)

- [x] Repeatable, seeded runs over public benchmarks (handle non-determinism) — SciFact adapter + ingested corpus + runner with `--repeats` and mean ± std
- [x] Full trace logging of every agent run
- [x] Metric suite: verification accuracy, hallucination-catch rate, false-agreement rate, latency p50/p95/p99, per-query cost
- [x] Single-LLM baseline harness for apples-to-apples comparison
- [x] Results tables auto-generated into `EVALUATION.md`
- [~] Literature check validating/refining the novelty claim — claim refined and scoped (`EVALUATION.md §8`); systematic validation deferred to Phase 6 (paper prep)

The harness is built and exercised offline; the **headline numbers** come from a live run
(`make phase3-bench`, which needs the ingested corpus and a provider key) and are written
into `EVALUATION.md §6.2` between the generated-table markers — not yet captured, so
nothing here is overstated.

## Phase 4 — Real-time frontend

- [x] Streaming of the live agent/verification path (SSE — `POST /verify/stream`)
- [x] Reasoning view, confidence score, and explicit disagreements (`/verify`)
- [x] Clean, legible, recruiter-impressive UI
- [x] Frontend tests for the streaming view (Vitest + RTL)

## Phase 5 — Production engineering

- [x] Resilient LLM client: per-provider retry/backoff (already in place) plus cross-provider fail-over (`LLM_FALLBACK_PROVIDER`) so an exhausted quota or outage no longer aborts a run
- [ ] Redis caching where it genuinely helps
- [ ] Prometheus + Grafana dashboards (latency / cost / agent metrics)
- [ ] OpenTelemetry-style tracing of agent runs
- [ ] Hardened Docker/compose and Kubernetes manifests
- [ ] Hardened CI/CD and a free-tier deployment

## Phase 6 — Paper & polish

- [ ] Finalize benchmark results
- [ ] Write the preprint from `EVALUATION.md`
- [ ] Prepare poster / demo
- [ ] Final repo polish — pristine and recruiter-ready

---

*Reporting checkpoints span June–October 2026; steady visible progress each
session is a first-class goal.*
