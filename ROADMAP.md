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
- [x] Infra baseline: Dockerfiles, `docker-compose.yml` (backend, frontend, postgres+pgvector; the redis service was later removed as unused — ADR-0008), `k8s/` placeholder
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
- [x] Guardrail layer — *delivered:* a non-mutating output advisory
  (info / caution / high-caution) plus a standing medical-advice disclaimer,
  on top of the Verifier's hard grounding rule. Input-side prompt-injection
  screening and scope filtering also landed as the **Intake guard** (PR #33):
  a deterministic injection scan plus an LLM scope check that refuses off-topic
  or adversarial input before any answer is generated
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
into `EVALUATION.md §6.2` between the generated-table markers.

### Phase 3.5 — scale & harden the headline run

- [x] Ungrounded multi-agent **ablation arm** (`--ablation`) — tests H2 directly (PR #39)
- [x] **Paired significance** on the headline gaps — exact McNemar + bootstrap CIs (PR #40)
- [x] Single-source **frontend results JSON** so the UI never drifts from `EVALUATION.md` (PR #42)
- [x] Real seeded **stratified sampling** (`--sample`) + a corpus-coverage check (A1, PR #45)
- [x] Per-item **fault tolerance** in the runner so one provider error can't abort a sweep (A3)
- [ ] The **scaled live run** — larger seeded sample, repeats, with the ablation arm (A5;
  free-tier-bounded, split across days for the token budget)

## Phase 4 — Real-time frontend

- [x] Streaming of the live agent/verification path (SSE — `POST /verify/stream`)
- [x] Reasoning view, evidence-support meter, and explicit disagreements (`/verify`)
- [x] Clean, legible, recruiter-impressive UI — the "Refined Luminous" redesign with an
  animated hero motif, a live pipeline, scroll-reveal/count-up motion, and a `/benchmark`
  page (all reduced-motion safe)
- [x] Frontend tests for the streaming view (Vitest + RTL)
- [x] Multimodal claim intake *(added after Phase 5)* — bring the claim as a PDF, a
  photo, or a voice note: `POST /extract` (pypdf / Gemini vision / Groq Whisper) fills
  the editable query field for review before verifying; strictly intake plumbing, the
  pipeline and harness untouched (ADR-0009)

## Phase 5 — Production engineering

- [x] Resilient LLM client: per-provider retry/backoff (already in place) plus cross-provider fail-over (`LLM_FALLBACK_PROVIDER`) so an exhausted quota or outage no longer aborts a run
- [x] Deployment decision + free-tier demo groundwork ([ADR-0007](docs/design/0007-free-tier-live-demo-deployment.md): Vercel + Neon + HF Spaces; per-IP rate limiter with a fail-loud production guard; [deploy guide](docs/deployment.md)) — live provisioning is a follow-through step
- [x] Right-sized observability: `/metrics`, per-stage duration histograms, structured JSON logs with request ids, local Grafana compose profile (`docker compose --profile obs up`)
- [x] Honest Redis decision: removed entirely — no code path used it and nothing at demo scale is worth caching ([ADR-0008](docs/design/0008-remove-redis.md)); the reintroduction shape is documented in the ADR
- [x] Reference k8s manifests (schema-validated in CI via kustomize + kubeconform, explicitly not a maintained target) + hardening quick wins (non-blocking pip-audit in CI, weekly Dependabot for uv/npm/actions, request body-size cap)

## Phase 6 — Paper & polish

- [ ] Finalize benchmark results
  - [x] Error analysis of the grounded arm's misses — offline `error_analysis` module +
    `make error-analysis`, tagging every miss (retrieval / verifier-abstention /
    wrong-direction / false-grounding); finding written into `EVALUATION.md §6.3`
    (retrieval is not the bottleneck; the dominant accuracy sink is over-assertion on
    NotEnoughInfo claims, an upper-bounded figure given open-corpus retrieval)
  - [ ] Stronger-model run — re-run the three-way sweep on a more capable verifier to test
    whether shrinking the false-grounding bucket lifts accuracy above the baseline
    (free-tier-bounded; paced / split across days)
- [ ] Write the preprint from `EVALUATION.md`
- [ ] Prepare poster / demo
- [ ] Final repo polish — pristine and recruiter-ready

---

*Reporting checkpoints span June–October 2026; steady visible progress each
session is a first-class goal.*
