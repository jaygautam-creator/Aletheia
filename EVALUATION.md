# Evaluation

> The evaluation harness is the **centerpiece** of Aletheia. This document is both
> the methodology of record and the spine of the research paper. It is populated
> with concrete numbers from Phase 3 onward; this Phase 0 version defines the plan
> and the contract for results.

## 1. Research question

> Does an evidence-grounded, multi-agent verification pipeline catch measurably
> more hallucinations than a single LLM, and at what latency and cost?

## 2. Hypotheses

- **H1 (catch rate).** Aletheia achieves a higher hallucination-catch rate than a
  single-LLM baseline on the same benchmark.
- **H2 (grounding reduces false agreement).** Requiring quoted-span evidence
  lowers the false-agreement rate compared with an otherwise-identical
  multi-agent arm whose verdicts are opinion-only (no span discipline) — the
  ablation arm defined in §5.
- **H3 (acceptable cost).** The reliability gains come at a quantified,
  defensible latency and per-query cost overhead.

## 3. Metrics

| Metric | Definition |
| --- | --- |
| **Verification accuracy** | Agreement of system verdicts with gold labels. |
| **Hallucination-catch rate** | Fraction of truly unsupported/false claims correctly flagged. |
| **False-agreement rate** | Fraction of cases where agents concur on a wrong verdict. |
| **Latency** | Wall-clock per query for each system's own verification work, reported as p50 / p95 / p99. Retrieval is shared across systems and held fixed, so it is measured once and excluded from the per-system figure (it is not part of what differs between them). |
| **Per-query cost** | Token/compute cost per query (free-tier token accounting). |

All metrics are reported **with the single-LLM baseline alongside**, so every
number is a comparison, not an absolute in a vacuum.

## 4. Datasets

The selected benchmark is **SciFact** (Wadden et al., *Fact or Fiction: Verifying
Scientific Claims*, EMNLP 2020; dataset `allenai/scifact`, CC BY-NC 2.0) — expert-written
scientific claims labelled against biomedical abstracts. It is chosen over the
general-domain candidates also considered (HaluEval; FACTS-style grounding sets) because
it is the strongest fit for this system:

- **Domain match.** Its claims and evidence are biomedical, so they can be grounded in the
  frozen PubMed/PMC corpus this project already curates (§5).
- **Label mapping.** Its claim-level labels map directly onto the pipeline's own verdict
  space — `SUPPORT → Supported`, `CONTRADICT → Contradicted`, *no evidence
  (NotEnoughInfo) → Unverifiable* — so a benchmark claim is exactly what the pipeline emits
  a verdict for, and gold and prediction are compared like with like.
- **Self-contained evidence.** SciFact ships its own corpus of abstracts, so growing the
  fixed corpus to cover the benchmark is a defined, reproducible ingest, not guesswork.

Selection criteria (unchanged): free to obtain, scriptable to download, well-cited, and
aligned with claim-level grounded verification.

As in §5, the dataset supplies the *claims and gold labels*; the *evidence* the system
grounds in is the fixed medical corpus — here, SciFact's abstract corpus ingested into the
frozen store. The two remain distinct: the corpus is what the Retriever searches, the claim
set is what the verdicts are scored against.

## 5. Experimental protocol

- **Non-determinism handling.** Each configuration is run multiple times with
  fixed seeds where supported; results report mean ± standard deviation.
- **Apples-to-apples baseline.** The single-LLM baseline uses the same model,
  prompt budget, and corpus access policy as the multi-agent system, differing
  only in the verification architecture.
- **Ablation arm (H2).** Alongside the two headline systems, the harness can run
  a third arm (`--ablation`): the *same* per-claim multi-agent critic with the
  span discipline removed — its prompt mirrors the grounded Verifier's word for
  word except that no quoted span is required, and its verdicts are taken as-is
  (never checked against the evidence text). All three arms judge the same claim
  against the same retrieved evidence with the same model. H1 is baseline vs
  grounded; H2 is ungrounded vs grounded — that gap isolates exactly what
  quoted-span grounding contributes, holding the multi-agent structure fixed.
  Reporting order everywhere: baseline → ungrounded → grounded.
- **Paired significance.** Because every system judges the *same* claims, headline
  gaps are tested on the paired per-claim predictions (of the first repeat), not on
  the two summary numbers: an **exact McNemar test** on the discordant pairs for
  verification accuracy, and **percentile-bootstrap 95% confidence intervals**
  (10,000 resamples, fixed seed, items resampled with their pairing intact) for the
  catch-rate and false-agreement deltas. The footnote is generated into §6.2
  together with the table.
- **Full trace logging.** Every run logs the complete agent path (inputs,
  retrieved spans, verdicts, timings) for auditability and error analysis.
- **Reproducibility.** A single command re-runs the suite; configuration is
  declared in code, not hand-tuned per run.
- **Fixed-corpus benchmarking.** All benchmark runs ground in the **frozen,
  versioned medical corpus** (PubMed / PMC open-access), so every headline number is
  reproducible: any reader can re-run the suite against the same corpus state and
  obtain the same result. The corpus is changed deliberately and noted, never
  drifted. The **live literature/web fallback is a demonstrated real-world
  capability, not a benchmarked component** — it is shown working in the demo and
  described qualitatively, but it never contributes to the headline metrics. This
  split keeps the centerpiece honest and defensible. See
  [`docs/design/0006`](docs/design/0006-benchmark-on-fixed-corpus.md) and
  [`docs/design/0003`](docs/design/0003-corpus-first-hybrid-knowledge-source.md).

## 6. Results

### 6.1 Phase 1 — preliminary comparison (thesis de-risking)

Phase 1 establishes the measurement machinery on a small, controlled set before
the full benchmark sweep of Phase 3. It is a *de-risking* experiment, not the
headline result.

- **Dataset.** A curated mini-set (`backend/.../evaluation/data/phase1_mini.jsonl`)
  of short evidence passages and candidate answers decomposed into atomic claims,
  each labelled supported / unsupported **relative to the evidence**. Some claims
  are deliberately planted: unsupported by the passage (whether contradicted or
  simply absent — including *true* facts the passage does not state).
- **What is held fixed.** Both systems judge the *same* atomic claims against the
  *same* evidence with the *same* model. Decomposition and retrieval are
  deliberately excluded so the comparison isolates one variable: evidence-grounded,
  per-claim verification with an enforced quoted span.
- **Systems.** *Single-LLM baseline* — one holistic call labelling every claim,
  with no span discipline. *Aletheia (grounded verifier)* — each claim judged
  independently and required to quote a verbatim span, with verdicts downgraded to
  `Unverifiable` when the span is missing or not found in the evidence.
- **Metrics.** Hallucination-catch rate (recall on unsupported claims),
  false-flag rate (supported claims wrongly flagged), and accuracy — reported side
  by side.
- **Reproduce.** `make phase1-demo` (requires a free provider key in `.env`).

First live run (2026-06-27, Groq), on the 8-item / 29-claim mini-set:

| Model | System | Catch rate | False-flag rate | Accuracy |
| --- | --- | --- | --- | --- |
| `llama-3.3-70b-versatile` | Single-LLM baseline | 8/8 (100%) | 0/21 (0%) | 100% |
| `llama-3.3-70b-versatile` | Aletheia (grounded verifier) | 8/8 (100%) | 0/21 (0%) | 100% |
| `llama-3.1-8b-instant` | Single-LLM baseline | 8/8 (100%) | 0/21 (0%) | 100% |
| `llama-3.1-8b-instant` | Aletheia (grounded verifier) | 8/8 (100%) | 1/21 (4.8%) | 96.6% |

> **Honest reading — this de-risks the machinery, it does not yet demonstrate the
> thesis.** The mini-set is *at ceiling*: even a small model nails the baseline
> (100% catch), so there is no error gap for grounding to close, and the grounded
> verifier's strictness can even cost a point (the 8B run false-flagged one
> genuinely-supported claim it could not quote cleanly). The *mechanism* is sound —
> it correctly refused to affirm an unsupported "designed by Gustave Eiffel" claim,
> marking it Unverifiable — but the aggregate comparison here is a tie, by design of
> the toy dataset. The demonstration that grounding *wins* lives in §6.2, on a
> harder, larger, retrieval-fed benchmark. Reproduce with `make phase1-demo`.

### 6.2 Phase 3 — headline benchmark

The table below is generated from a live run — `make phase3-bench CLAIMS=…` invoked with
`--write-eval EVALUATION.md` — and refreshed in place between the markers. Until the first
live run it shows the table's shape with placeholder values.

<!-- PHASE3:BEGIN -->
_SciFact · 20 claims · 1 seeded run · mean ± std._

| System | Verif. accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 65.0% ± 0.0% | 58.3% ± 0.0% | 41.7% ± 0.0% | 15.679 / 19.600 / 19.787 | 1474.6 |
| Aletheia (grounded verifier) | 75.0% ± 0.0% | 91.7% ± 0.0% | 16.7% ± 0.0% | 15.660 / 19.992 / 20.597 | 1649.8 |
<!-- PHASE3:END -->

**Run provenance (2026-06-30).** Both systems judge the *same* claim against the *same*
evidence, retrieved by hybrid search over the **full SciFact corpus (5,183 abstracts,
15,411 chunks)** ingested into pgvector. Claims are the first **20** of the SciFact `dev`
split. Model: **Groq `llama-3.1-8b-instant`** for *both* the grounded verifier and the
single-LLM baseline (the apples-to-apples comparison holds regardless of which model is
used) — chosen because the larger default models' free-tier **daily token caps were
exhausted** on the run date. A single seeded repeat is reported, so the ± is 0.0; the
harness supports `--repeats N` for mean ± std, and a larger claim count, once token budget
allows. These are **free-tier-bounded** numbers, not a final benchmark.

Even at this scale the direction is clear and matches the thesis: the grounded verifier
**catches more errors** (91.7% vs 58.3%) and **agrees with far fewer wrong claims**
(false-agreement 16.7% vs 41.7%), for ~12% more tokens and no latency penalty. Scaling to
the full dev split with seeded repeats (and the stronger model once quota resets) is the
next step.

Per-dataset breakdowns, ablations (e.g., grounding on/off), and error analysis
will accompany the headline table.

## 7. Threats to validity

- **Benchmark leakage / contamination** into pretraining — mitigated by reporting
  the *relative* gap to the baseline rather than absolute scores.
- **Prompt sensitivity** — controlled by holding prompts fixed across systems and
  reporting variance across runs.
- **Retriever ceiling** — verification can only ground in what is retrievable;
  retrieval quality is measured and reported separately.

## 8. Novelty claim (positioning)

Two large bodies of prior work bracket this project. **Claim verification /
fact-checking** labels a claim against retrieved evidence — e.g. FEVER (Thorne et al.,
2018) over Wikipedia and SciFact (Wadden et al., 2020) over scientific abstracts — while
**hallucination detection and self-verification** flag unsupported model output, e.g.
SelfCheckGPT (Manakul et al., 2023) and Chain-of-Verification (Dhuliawala et al., 2023).
Separately, **multi-agent** methods improve factuality through natural-language debate or
critique among model instances (e.g. Du et al., 2023).

Aletheia sits at the intersection these mostly leave open: a **multi-agent verification
pipeline whose agreement is constrained by evidence** — a verdict may affirm or contradict
a claim only by quoting a verbatim source span, and is forced to `Unverifiable` otherwise —
delivered as a **deployed, evaluated** service with a **reusable, seeded harness** that
reports catch rate, false-agreement, latency, and cost against a single-LLM baseline on a
fixed, citable corpus. The contribution is the *combination*, not a new detector or a new
debate protocol: span-grounded agreement structurally defeats the false-agreement failure
mode that opinion-only debate is prone to, inside an end-to-end, benchmarked system.

This is a **positioning** claim, not a systematic survey. To our knowledge this specific
combination is not occupied by an existing system, but that priority claim is deliberately
*not* the headline — the honest, defensible unit is the **measured gap to the baseline**
(§6). The citations above are landmark references; the novelty framing and bibliography are
to be validated against a structured literature search at paper-writing time (Phase 6).
