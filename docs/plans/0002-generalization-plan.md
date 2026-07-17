# Generalization Plan — July 2026

> **Status:** Active. Green-lit by the author on 2026-07-17, alongside the
> definitive n=100 re-validation of the improved verifier (which runs
> separately and stays the headline). Each item below is a small, CI-green PR
> in the project's normal workflow (feature branch → PR → merge). Items marked
> **[deep]** need careful design judgement; items marked **[spec]** can be
> implemented directly as written.
>
> Ground rules that bind every PR (unchanged from the charter and plan 0001):
> free-tier only · verdict contract changes are additive-only · offline tests
> with fakes/fixtures (live numbers only from `make` runs, never in tests) ·
> all four backend gates (`ruff check`, `ruff format --check`, `mypy`,
> `pytest`) plus the frontend gates pass locally before pushing · author-only
> attribution.

## 0. Scope decision — what "anyone can bring any claim" means here

The author's ask is that Aletheia should not feel limited to medical claims.
The charter already constrains how that can happen: no general-purpose chatbot,
no open-web retrieval (ADR-0003: corpus-first; ADR-0006: benchmark on a fixed
corpus), no sprawl into many domains — but the engine is deliberately
**domain-agnostic with pluggable corpus connectors** (ADR-0001). Two deliveries
fit inside those walls, and together they cover the ask:

- **Workstream E — a second, general-domain benchmark (FEVER).** Wikipedia
  claims about anything — history, sport, politics, culture. This is the
  *measured* generalization story: a second corpus connector and a second
  results table proving the engine's advantage is not a SciFact artifact.
- **Workstream F — verify against your own document.** The *product*
  generalization story: the user supplies the evidence, so any genre works
  without touching the corpus or the benchmark. The pipeline already supports
  caller-supplied evidence end-to-end; this surfaces it.

Explicitly **not** in scope: live web retrieval, a third benchmark domain, or
any open-ended "ask me anything" chat surface.

---

## Workstream E — FEVER general-domain benchmark

### E0. ADR-0011: a second benchmark domain on a scoped corpus — [deep]

Record the decision before any code:

- **Dataset:** FEVER (fever.ai) — 145K Wikipedia claims labelled
  `SUPPORTS` / `REFUTES` / `NOT ENOUGH INFO`, mapping cleanly onto the verdict
  contract (`Supported` / `Contradicted` / `Unverifiable`). Free download;
  Wikipedia-derived content under CC BY-SA. Dataset files stay gitignored
  under `backend/data/fever/` like SciFact.
- **Corpus scoping:** the full FEVER wiki dump is ~5.4M pages — not
  free-tier-ingestable. We build a **seeded, closed corpus slice**: every page
  cited by the sampled claims' gold evidence, plus seeded random distractor
  pages, targeting a corpus of the same order as SciFact (~5K documents).
- **Honest limitation, written into the ADR and EVALUATION.md:** closed-corpus
  retrieval is easier than full-Wikipedia FEVER, so our numbers are *not*
  comparable to FEVER-shared-task systems. That is consistent with ADR-0006 —
  the research question is grounded-vs-baseline on a fixed corpus, not
  open-domain retrieval state of the art.

### E1. FEVER corpus connector — [spec]

`corpus/connectors/fever.py`, following `scifact.py`'s shape: connector id
`fever`, `external_id` = the wiki page id, title from the page id, body from
the dump's sentence-numbered text (strip the sentence indices). A short
`backend/data/fever/README.md` documents the download URLs and license. Unit
tests run offline against a tiny checked-in fixture (a handful of fabricated
page lines), exactly like the SciFact connector tests.

### E2. Seeded corpus-slice builder — [spec]

A deterministic builder (new `evaluation/` or `corpus/` helper + CLI entry):
given the FEVER dev claims file, a sample size, and a seed, it (1) draws the
gold-label-stratified claim sample with the existing `stratified_sample`
machinery, (2) collects every evidence page those claims cite, (3) adds seeded
distractor pages up to the corpus target, and (4) writes `corpus_fever.jsonl`
for the normal ingest path, recording the slice parameters in the corpus
manifest so provenance is reproducible. The slicing logic is pure and
unit-tested; the dump-reading edge is thin.

### E3. Benchmark adapter — [spec]

`evaluation/dataset.py` gains a FEVER loader producing `BenchmarkItem`s:
claim text, mapped gold label, `cited_doc_ids` from the evidence annotations
(`NOT ENOUGH INFO` claims cite nothing, which the coverage check must treat as
covered). `phase3.py` gains `--dataset {scifact,fever}` (default `scifact`) to
select loader and default paths. **The §6.2 SciFact markers are untouched**:
FEVER results render between new markers in a new `EVALUATION.md` section
("Generalization to a second domain"), and the frontend results JSON grows a
`domain` field with the frontend reading it defensively (missing field =
`scifact`, so the page never breaks on the old file).

### E4. Live FEVER run + write-up — [deep]

Same protocol as the SciFact headline: seeded stratified n=100, three arms,
exact McNemar + bootstrap CIs, Groq `llama-3.1-8b-instant`, `--pace-seconds`
sized to the 6K TPM cap. Budget: ~460K tokens ≈ one full free-tier day, so
this run gets its own session, like the SciFact re-validation. Write-up adds
the generalization section to `EVALUATION.md`, a second domain card on
`/benchmark`, and the honest caveat from E0.

---

## Workstream F — verify against your own document

The backend already does most of the work: `POST /verify` accepts an optional
`evidence` string, and the Retriever runs only when no evidence is supplied.
One backend decision was needed on top — the intake guard's medical-scope
classifier used to decline non-medical queries even when the caller brought
the evidence. ADR-0010 resolves it: the scope rule guards the corpus, not the
engine, so caller-supplied-evidence requests skip the classifier (the
injection scan always runs). Everything else below is presentation-layer —
the verdict contract and harness are untouched.

### F1. Evidence-source toggle on `/verify` — [spec]

The verify page gains an evidence-source control: **"Search the corpus"**
(today's behavior, default) vs **"My document"**, which reveals an evidence
editor. The existing intake chips (PDF / photo / voice via `POST /extract`)
are reused so an upload can fill *either* the query field (today) or the
evidence editor (new) depending on the active mode; extracted text stays
editable before anything runs, exactly like the query path (ADR-0009's
review-before-verify rule). The request simply includes `evidence`, and the
existing streaming view renders as normal. State changes live in the reducer
with unit tests; the presentational component is tested with crafted states,
per the house pattern.

### F2. Truthful provenance labeling — [spec]

When verdicts are grounded against a user document, the citations panel must
say so: a clear "your document" provenance card instead of corpus citations,
with no trust-tier badge implied (user evidence is unranked — it is whatever
the user pasted). The standing research-tool disclaimer is unchanged. README
and `ARCHITECTURE.md` get a short truthful note that evidence can be caller-
supplied end-to-end.

---

## Sequencing and budget

1. **F1 → F2 first** — quota-free, two small PRs, immediate product payoff,
   and they make the multimodal intake feature more useful the day they land.
2. **E0 → E3** next — all offline, CI-green, reviewable one PR at a time.
3. **E4 last** — the only live-quota step, scheduled for a day whose Groq
   budget is not needed by the SciFact re-validation or its follow-ups.

The definitive SciFact n=100 re-validation (running separately) remains the
paper's headline; FEVER lands as its generalization evidence, not its
replacement.
