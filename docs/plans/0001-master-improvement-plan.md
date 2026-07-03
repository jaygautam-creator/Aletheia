# Master Improvement Plan — July 2026

> **Status:** Active. Written after a full audit of the codebase, architecture,
> documentation, and roadmap (2026-07-02). This is the working plan for the next
> stretch of sessions. Each item below is a small, CI-green PR in the project's
> normal workflow (feature branch → PR → merge). Items marked **[deep]** need
> careful design judgement and review; items marked **[spec]** are fully
> specified here and can be implemented directly as written.
>
> Ground rules that bind every PR (unchanged from the charter):
> free-tier only · verdict contract changes are additive-only · offline tests
> with fakes/fixtures (live numbers only from `make` runs, never in tests) ·
> all four backend gates (`ruff check`, `ruff format --check`, `mypy`, `pytest`)
> plus the frontend gates pass locally before pushing · author-only attribution.

## 0. Audit verdict — what is sound and stays

The audit found **no architectural problems**. The following are correct and
must not be reworked:

- **The pipeline shape** (`agents/graph.py`): Intake guard → (Retriever) →
  Generator → Verifier → Aggregator → Guardrail-last-and-advisory, as a linear
  LangGraph state machine. It is exactly what a traceable evaluation needs.
- **The verdict contract** (`agents/contracts.py`): the two-layer grounding
  enforcement (shape validation + `grounded_against` downgrade) is the core
  thesis made structural. Never weaken it; only add optional fields.
- **The LLM layer**: provider-agnostic `LLMClient`, per-provider tenacity
  retries, `FallbackLLMClient` chain, `RecordingLLMClient` for cost. Solid.
- **Hybrid retrieval** (`corpus/retrieval.py`): pgvector + tsvector fused with
  RRF, pure-function core, DB-backed integration tests in CI. Solid.
- **The harness structure** (`evaluation/`): pure metrics, adapter, traces,
  markdown generation into `EVALUATION.md` markers. Right seams, right tests.
- **Frontend engineering**: pure reducer + `parseSSE` unit-tested without
  React; presentational `VerificationView` tested with crafted states. Keep
  this pattern for every frontend change below.

What needs work, in priority order: **(A)** the evaluation evidence is too thin
to carry the thesis yet (n=20, no real seeding, no ablation, no significance);
**(B)** several documents no longer tell the truth about the code;
**(C)** the landing and verify pages are engineering-clean but product-thin;
**(D)** the Phase 5 list should be re-scoped toward what the capstone/paper
actually needs.

---

## Workstream A — Evaluation rigor (highest priority: this is the centerpiece)

### A1. Real seeded sampling + corpus-coverage check — [spec]

**Problem.** `phase3.py` claims "seeded runs" but has no `--seed`; `--limit N`
takes the *first N* claims of `claims_dev.jsonl` (a non-random, possibly biased
sample), and `--repeats` re-runs the identical items (variance comes only from
provider non-determinism). `BenchmarkItem.cited_doc_ids` exists "to check corpus
coverage" but nothing checks it.

**Change** (in `backend/src/aletheia/evaluation/phase3.py` + `benchmark.py`):

1. Add `--seed INT` (default 7) and `--sample N` to the CLI. `--sample` draws a
   **stratified** random sample without replacement using `random.Random(seed)`:
   proportional allocation across the three gold labels (Supported /
   Contradicted / Unverifiable), remainder to the largest stratum. Keep
   `--limit` (head-slice) for smoke runs; `--sample` and `--limit` are mutually
   exclusive (`parser.error` if both).
2. Pure helper in `benchmark.py`:
   `stratified_sample(items: Sequence[BenchmarkItem], n: int, *, seed: int) -> list[BenchmarkItem]`
   — deterministic for a given seed; unit-test with hand-built items (exact
   membership for a fixed seed, per-label proportions, n > len(items) returns all).
3. Corpus coverage: async helper `corpus_coverage(session, items) -> Coverage`
   (frozen dataclass: `n_items`, `n_covered`, plus `fraction` property) that
   checks which items have **all** their `cited_doc_ids` present among ingested
   SciFact source `external_id`s (one `SELECT external_id FROM source WHERE
   connector = 'scifact'`, then set logic — set logic stays pure/unit-testable).
   Print coverage before the run; warn loudly under 95%.
4. Provenance into the generated §6.2 block: extend `render_markdown` so the
   italic caption line carries `n`, `seed`, `repeats`, `model`
   (`llm.provider:llm.model`), coverage %, and the run date. The live table must
   be self-describing.
5. Report the sample's gold-label distribution in stdout (e.g.
   `Supported 83 · Contradicted 41 · Unverifiable 26`).

**Definition of done:** offline tests for sampling determinism, stratification,
coverage set-logic, and the new caption; `make phase3-bench` unchanged for old
flags; docs strings updated. No live calls in tests.

### A2. Third arm: ungrounded multi-agent ablation (tests H2 directly) — [deep]

**Problem.** Hypothesis H2 (`EVALUATION.md §2`) says span-grounding lowers false
agreement "compared with opinion-only multi-agent debate" — but the harness has
only two arms (grounded vs single-LLM). The scientifically decisive comparison
for the paper is missing: the *same* per-claim multi-agent structure **without**
the span discipline.

**Change:**

1. New prompt in `agents/prompts.py`: `_VERIFY_UNGROUNDED` — identical framing
   to `_VERIFY` but verdicts are unconstrained opinions: no quoted-span
   requirement, JSON `{"verdict": ..., "reasoning": ...}`.
2. In `phase3.py`: `ungrounded_claim_verdict(llm, claim, evidence) -> Verdict` —
   same per-claim call pattern as the grounded arm, but the parsed verdict is
   used as-is (no `grounded_against`, no downgrade).
3. `--ablation` CLI flag adds the third system to the run; `BenchmarkReport`
   gains `ungrounded: SystemReport | None = None`; `report.py` renders a third
   table row when present. Keep the two-arm table byte-identical when the flag
   is off (existing tests must not change).
4. `EVALUATION.md §5` gains one paragraph defining the three arms.

**Why [deep]:** the ungrounded prompt must be *fair* — as close to the grounded
prompt as possible so the only variable is the span discipline. Wording choices
here are methodology, not plumbing. Draft the prompt, then review it against
`_VERIFY` line by line before merging.

### A3. Per-item fault tolerance in the runner — [spec]

**Problem.** One `LLMError` mid-run aborts the whole sweep with nothing saved
(observed live on 2026-06-30 with a Groq timeout; the fallback client reduces
but does not eliminate this).

**Change** (in `phase3.py`):

1. Wrap each item's grounded+baseline(+ablation) calls in `try/except LLMError`;
   on failure record the item id + error, **skip the item in scoring** (do not
   fabricate a verdict), continue.
2. Track failures; print a `FAILED k/n items: [ids…]` summary; if
   `failures > --max-failures` (default 5) abort with partial traces written.
3. Scored lists must stay **paired**: an item that fails in *either* arm is
   excluded from *both* (all comparisons remain apples-to-apples).
4. Tests: fake LLM that raises on the k-th call → run completes, pairing holds,
   summary counts correct, exit is non-zero when any item failed.

### A4. Statistical honesty: paired significance on the headline gap — [deep]

**Problem.** n=20 with a single run supports no claim of a real gap. The paper
needs uncertainty quantified on *paired* predictions.

**Change** (in `evaluation/metrics.py`, pure functions + tests only):

1. `mcnemar_exact(b: int, c: int) -> float` — exact binomial McNemar p-value on
   the discordant pairs (baseline-right/grounded-wrong = b, vice versa = c) for
   verdict-accuracy; document the definition in the docstring.
2. `paired_bootstrap_delta(pred_a, pred_b, gold, metric, *, n_resamples=10_000,
   seed) -> ConfidenceInterval` — percentile 95% CI for the metric delta
   (works for catch-rate and false-agreement deltas), deterministic under seed.
3. `phase3.py` computes both on the *first* repeat's paired predictions and
   appends one footnote line under the §6.2 table, e.g.
   `Accuracy gap: McNemar exact p = 0.031 · catch-rate Δ 95% CI [+8.3, +41.7] pp (paired bootstrap, seed 7).`
4. Tests with hand-computable cases (small b/c values; a degenerate CI when
   predictions are identical).

**Why [deep]:** picking the right test and stating it correctly is
paper-methodology; get the definitions reviewed before they go into
`EVALUATION.md`.

### A5. The real headline run — [spec, but run by Jay]

Once A1–A4 are merged, run live (needs Postgres up, corpus ingested, Groq key):

```bash
make db-upgrade
uv --directory backend run python -m aletheia.evaluation.phase3 \
  --claims data/scifact/claims_dev.jsonl \
  --sample 150 --seed 7 --repeats 3 --ablation \
  --traces runs/scifact_dev_n150.jsonl --write-eval ../EVALUATION.md
```

- Model: `LLM_MODEL=llama-3.1-8b-instant` (per-model daily token budget is the
  binding constraint; both/all arms share the model so the comparison holds).
  Budget check first: ~150 claims × 3 repeats × 3 arms × ~1.6k tokens ≈ 2.2M
  tokens — **split across days** (one repeat per day ≈ 720k) or reduce to
  `--sample 100`. The runner prints token totals; stop before the cap.
- Afterwards: refresh the README table, `PROGRESS_LOG.md`, and the frontend
  results JSON (A6). Only then may the n=20 caveats be softened.

### A6. One source of truth for the numbers the frontend shows — [spec]

**Problem.** `frontend/components/BenchmarkChart.tsx` hardcodes the metrics in a
TSX constant; it *will* silently drift from `EVALUATION.md` after A5.

**Change:**

1. `--write-frontend PATH` flag in `phase3.py` writing
   `frontend/lib/benchmark-results.json`:
   `{ "dataset", "n", "seed", "repeats", "model", "date",
      "systems": [{ "name", "accuracy", "catch_rate", "false_agreement", "latency_p50", "tokens_per_query" }] }`
   (percentages as numbers, one decimal). Commit the generated file.
2. `BenchmarkChart` imports the JSON (typed via a `BenchmarkResults` interface
   in `lib/verification.ts` or a new `lib/benchmark.ts`); the caption (n, seed,
   model, date) renders from it too. Delete the hardcoded `METRICS`.
3. Vitest: chart renders values from a fixture JSON.

---

## Workstream B — Documentation truth pass (cheap, do early)

### B1. `ARCHITECTURE.md` no longer matches the code — [spec]

The §2 component map and §3 sequence diagram show the **old** design: Guardrail
*first* screening inputs, and Generator → Retriever order. Reality
(`agents/graph.py`): **Intake guard** (deterministic injection scan + LLM scope
classifier, fail-open) → conditional refusal path → **Retriever (optional) →
Generator → Verifier → Aggregator → Guardrail last, advisory-only,
never edits a verdict**. Rewrite both diagrams and the §4 component table
(add Intake row; fix Guardrail row), update §5 repo layout (the harness lives in
`backend/src/aletheia/evaluation/`, not `eval/` — see B2), and extend §7 status
through Phase 4 + the Phase 5 items already landed (fallback chain, intake
guard). Verify every statement against the current source before writing it.

### B2. `eval/README.md` describes a directory that never happened — [spec]

It still shows a "planned layout" (`eval/datasets/`, `eval/runners/`…). The
harness lives in `backend/src/aletheia/evaluation/`. Rewrite the README as a
short pointer: where the harness actually lives, the `make phase1-demo` /
`make phase3-bench` entry points, where results land (`EVALUATION.md` §6), and
why it is inside the backend package (imports the pipeline directly; one lock
file; tested by the same CI). Keep the `eval/` directory only if it will hold
run artifacts; otherwise delete it and fix references (README table,
ARCHITECTURE §5).

### B3. `EVALUATION.md` gaps — [deep]

1. **§6.1 is still `_live run_` placeholders** even though the Phase 1 live run
   happened (2026-06-27, Groq): 70B — baseline and grounded both 100% (tie at
   ceiling); 8B — baseline 100%, grounded 96.6% (one strict-quote false flag).
   Record these numbers **with the honest reading**: the mini-set is at
   ceiling, it de-risks the machinery but does not demonstrate the thesis;
   the demonstration lives in §6.2. (Honesty is a project non-negotiable —
   this table currently *understates* what was done, which is its own kind of
   inaccuracy.)
2. **§3 latency definition** says "end-to-end wall-clock per query" but the
   harness times only each system's verification call — retrieval is shared and
   deliberately excluded (`phase3.py` module docstring). Fix the definition to
   say exactly that.
3. After A2/A4/A5: update §5 (three arms, significance protocol) and let the
   generated §6.2 carry the new provenance caption.

### B4. `ROADMAP.md` adjustments — [spec]

- Phase 2 guardrail item is `[~]` with input-side screening "deferred to Phase
  5" — the intake scope/injection guard landed (PR #33). Tick it, note where.
- Phase 5: replace the current list with the re-scoped one from Workstream D.
- Add the A-items under Phase 3 as "3.5 — scale + harden the headline run"
  checkboxes so the roadmap shows why the benchmark work continues.

### B5. Repo hygiene — [spec]

- `RUN.md` (untracked): fold its useful content into `CONTRIBUTING.md` (or
  commit it as-is if Jay prefers a separate quick-start; it currently says the
  UI "is skeletal", which is stale — update while moving).
- `.wiki/` (untracked): GitHub wikis are a **separate** git repository
  (`Aletheia.wiki.git`); either push the content there and delete the local
  copy, or stop maintaining it. It must not silently rot inside the main repo.
- `.env.example`: make sure it reflects the working setup (Groq primary,
  fallback chain, `SCOPE_GUARD_ENABLED`), since README quick-start points
  Gemini-first while the live setup runs Groq.

---

## Workstream C — Frontend product quality

Design system stays **Clinical Luminous** (bone canvas, ink-navy text,
teal→cyan accent, Fraunces display serif, CSS-only motion, reduced-motion
respected). Every new section must use the existing tokens/utilities — no new
color families, no component libraries. Keep the pure-reducer/presentational
split and extend the Vitest suites with every change.

### C1. Landing page: show the product, not just claims about it — [spec]

Current page = hero → chart → 5 pipeline cards → 3 principle cards → footer.
It never shows the product's most convincing artifact: **a grounded verdict**.
Restructure `app/page.tsx` to:

1. **Hero** — keep as is (copy is good).
2. **Example verification (new, the money shot):** a static, honest specimen of
   the real output — the claim *"Aspirin reduces the risk of first heart attack"*
   style card reusing the exact visual language of `ClaimCard`/`Citations`
   (verdict chip, quoted-span blockquote with the teal left border, source line
   with trust tier). Content must be a **real** pipeline output (run once, paste
   verbatim, caption it "actual output, corpus of 5,183 abstracts"). Implement
   as a presentational `ExampleVerdict` component with the data in a typed
   constant; add a "Run your own →" link to `/verify`.
3. **Benchmark section** — keep `BenchmarkChart`, now fed from
   `benchmark-results.json` (A6), with the provenance caption from the JSON and
   a "How we measure → EVALUATION.md" link (GitHub URL).
4. **How it works** — three short numbered steps in plain language (retrieve
   real literature → decompose into atomic claims → every verdict must quote a
   span or admit Unverifiable). The pipeline strip moves *under* this as the
   technical detail, so a non-expert gets the story before the jargon.
5. **Safety boundary strip** — one quiet, always-visible sentence-card: research
   tool, verifies against literature, not medical advice (ADR-0002 requires the
   disclaimer be present in the UI, not only on `/verify`).
6. **Footer** — links: GitHub · EVALUATION.md · ARCHITECTURE.md · MIT © 2026 Jay
   Gautam.

Tests: extend `page.test.tsx` for the new sections (example verdict renders its
chip/span; footer links present).

### C2. Verify page: make the demo effortless — [spec]

1. **Example chips (highest demo value):** 4–5 curated one-click examples under
   the query field (mix of a supported claim, a contradicted one, an
   out-of-corpus one that comes back Unverifiable, and one out-of-scope query
   that shows the refusal card). Clicking fills the query and submits. Curate
   the list by actually running candidates against the corpus and picking ones
   with clean, fast, illustrative outcomes; keep them in a typed constant with a
   comment of the expected outcome.
2. **Cancel:** expose `cancel()` from `useVerificationStream` (the
   `AbortController` already exists) and render a Cancel button while streaming;
   aborting returns state to `idle` (new `"cancel"` action in the reducer, pure,
   tested).
3. **`?q=` deep link:** replace the `setTimeout` workaround with
   `useSearchParams` (wrap the reading component in `<Suspense>` per Next.js
   requirement) and **auto-submit** when `q` arrives so shared links replay the
   verification. `ShareButton` should only offer sharing after a run has
   started (it currently pushes a URL for text the user may never verify).
4. **Label honesty (ADR-0005):** the meter is `support_ratio`, deliberately
   *not* calibrated confidence (`contracts.py` says so). Rename the UI label
   from "Confidence" to **"Evidence support"** with the sub-line already there
   ("N of M claims grounded in evidence"). Update `stageSummary`'s aggregator
   line ("X% supported", not "X% confidence") and all affected tests.
5. **Active-stage feel:** while a stage is `active`, show a live elapsed ticker
   (`setInterval`, cleared on unmount/stage change) next to it, so 10-second
   free-tier calls read as "working", not "hung".
6. **Connection empathy:** when `fetch` fails outright (backend down), show a
   specific hint ("The API isn't reachable — is the backend running? `make dev`")
   instead of the raw error string.
7. **Order claims flagged-first** in the Claims list (Contradicted, then
   Unverifiable, then Supported) — the reader's eye should hit the problems
   first (ADR-0004: surface disagreement).

### C3. `/benchmark` page — [spec]

A small static route that renders `benchmark-results.json`: headline table
(all systems), the bar chart (reuse `BenchmarkChart`), the provenance block, a
short methodology summary (three-arm design, seeded sampling, paired
significance — mirror §5/§6.2 language), and links to `EVALUATION.md` and the
traces. Add "Benchmark" to the nav. This turns the centerpiece into a visible
product surface instead of a markdown file.

### C4. Link each quoted span to its source — [deep]

**Gap:** a verdict quotes a span, and citations list sources, but nothing
connects them. **Change:** at the API layer (not the contract): in
`verify.py`, when `evidence_sources` are present, resolve each grounded
verdict's span to the numbered evidence block that contains it (reuse the same
whitespace-normalisation as `contracts._normalised`; factor that helper out so
both share it) and add `"source_index": n` to the verdict payloads in both
`/verify` and `/verify/stream` serialisation. Additive and optional — the
`ClaimVerdict` pydantic contract itself is untouched. Frontend: a small `[n]`
chip on the blockquote linking (anchor scroll) to the citation entry.
**Why [deep]:** span→block resolution has edge cases (span straddling the
header line, span appearing in two blocks — pick the first; span not found —
omit the field) that need deliberate handling + tests on the formatted-evidence
format from `format_evidence`.

---

## Workstream D — Phase 5, re-scoped to what the capstone needs

The current Phase 5 list (Redis, Prometheus+Grafana, OTel tracing, hardened
k8s, CI/CD + deployment) is generic production engineering. Re-scope it around
two questions: *what makes the paper stronger* and *what makes the demo
reachable by a recruiter*. Replace the roadmap list with:

### D1. Deployment decision + free-tier live demo — [deep]

Write **ADR-0007** choosing the deployment shape, then implement it. The
realistic free-tier layout to evaluate first: **Vercel** (frontend, free),
**Neon** free Postgres with pgvector (SciFact corpus ≈ 15.4k chunks × 384-dim
≈ well within the free tier), backend container on **Render free** or
**HF Spaces** (accepting cold starts — the UI's connection-empathy state from
C2.6 should mention "the demo may take ~1 min to wake"). Corpus is ingested
once from the local machine to Neon. Keys: Groq free key as a server-side env
var **with the scope guard ON and a strict rate limit** (add a simple
per-IP limiter middleware, e.g. token bucket in-process, before exposing a
public endpoint). If the cold-start/ops cost proves unreasonable, the honest
fallback is a **recorded demo + one-command local run**, decided in the ADR —
not a half-deployed service.

### D2. Observability, right-sized — [spec]

- `/metrics` Prometheus endpoint (`prometheus-fastapi-instrumentator` or a
  hand-rolled minimal registry) + per-stage duration histograms: time each
  graph node by wrapping `astream` updates (the stage timings already exist in
  the stream path — record them server-side too).
- Structured JSON logs with a request id middleware.
- One committed Grafana dashboard JSON + a `docker compose --profile obs`
  adding Prometheus+Grafana for local use. **No k8s observability stack.**

### D3. Redis: decide honestly, then do at most one thing — [spec]

Redis is in the compose file but unused. Write the decision down (small ADR or
ARCHITECTURE §6 row): the one genuinely useful cache here is
**query → retrieval results** (embedding + two SQL branches + RRF ≈ the
expensive, deterministic part). If kept: `RedisRetrievalCache` wrapping
`Retriever.search` (key = normalised query + corpus manifest hash, TTL 1h,
guarded by optional `REDIS_URL` setting, `fakeredis` tests, cache disabled →
behaviour byte-identical). If not kept: remove Redis from compose + docs.
Do not cache LLM outputs (defeats the live-verification demo).

### D4. k8s: reference manifests only — [spec]

Minimal `infra/k8s/`: Deployment+Service for backend and frontend, a StatefulSet
for Postgres, kustomize base, a README saying explicitly these are reference
manifests validated with `kubectl apply --dry-run=client` / `kubeconform` in CI,
not a maintained production target. Anything more is scope theater for a
solo free-tier project.

### D5. Optional hardening quick wins — [spec]

- Backend: `pip-audit` (or `uv audit` when stable) step in CI, non-blocking at
  first; Dependabot config for npm + uv + actions.
- API: request-size limits and a `429` rate-limit response shape (shared with
  D1's limiter).

---

## Phase 6 (paper) — early notes so nothing above is wasted

- The paper's results section is §6.2 + the A4 significance lines + the A2
  ablation — that is the whole story arc (single-LLM < ungrounded multi-agent <
  grounded multi-agent, with CIs). Keep `EVALUATION.md` the single source.
- Error analysis: A3's failure records + the traces JSONL are the raw material;
  plan one session tagging ~30 grounded-arm errors by cause (retrieval miss vs
  verifier strictness vs gold-label subtlety). The strict-quote false-flag from
  Phase 1 (8B) is already one documented specimen.
- The §8 novelty claim stays a positioning claim until the Phase 6 structured
  literature search; do not harden its wording before then.

---

## Sequencing and model assignment

Order (each row = one PR unless noted):

| # | Item | Model | Status |
|---|------|-------|--------|
| 1 | B1 + B2 (docs truth) | Sonnet | ✅ merged (PR #44, with B3–B5) |
| 2 | A1 sampling + coverage | Sonnet | ✅ merged (PR #45) |
| 3 | A3 fault tolerance | Sonnet | ✅ merged (PR #46) |
| 4 | A2 ablation arm | **Fable** | ✅ merged (PR #39) |
| 5 | A4 significance | **Fable** | ✅ merged (PR #40) |
| 6 | B3 EVALUATION.md updates | **Fable** | ✅ merged (PR #44) |
| 7 | A5 live run (n≈100–150, ×3, ablation) | Jay + either | ✅ n=100 single-repeat run landed (PR #64); grounded catch 70.7% vs 60.3% baseline, +10.3pp CI [+3.3,+18.6]. ×3 repeats + stronger model remain (token budget) |
| 8 | A6 results JSON + chart rewire | Sonnet | ✅ merged (PR #42) |
| 9 | C2 verify-page UX | Sonnet | ✅ merged (PR #41) |
| 10 | C1 landing page | Sonnet | ✅ merged (PRs #41, #43 — Refined Luminous) |
| 11 | C3 /benchmark page | Sonnet | ✅ merged (PR #43) |
| 12 | C4 span→source linking | **Fable** | ✅ merged (PR #47) |
| 13 | B4 + B5 roadmap/hygiene | Sonnet | ✅ merged (PR #44) |
| 14 | D1 deployment ADR + deploy | **Fable** (ADR) then Sonnet (impl) | ✅ merged (PR #49) — ADR-0007 + limiter + guide; platform provisioning is Jay's follow-through |
| 15 | D2 observability | Sonnet | ✅ merged (PR #50) |
| 16 | D3 Redis decision + cache | Sonnet | ✅ merged (PR #51) — decision: removed (ADR-0008) |
| 17 | D4 k8s reference + D5 hardening | Sonnet | ✅ merged (PR #52) |

Session ritual reminder for every PR: update `ROADMAP.md` checkboxes,
`PROGRESS_LOG.md` (plain language, newest first), `EVALUATION.md` when numbers
change, README status when a phase moves — then feature branch → PR → CI green
→ merge.
