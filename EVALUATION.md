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
  lowers the false-agreement rate compared with opinion-only multi-agent debate.
- **H3 (acceptable cost).** The reliability gains come at a quantified,
  defensible latency and per-query cost overhead.

## 3. Metrics

| Metric | Definition |
| --- | --- |
| **Verification accuracy** | Agreement of system verdicts with gold labels. |
| **Hallucination-catch rate** | Fraction of truly unsupported/false claims correctly flagged. |
| **False-agreement rate** | Fraction of cases where agents concur on a wrong verdict. |
| **Latency** | End-to-end wall-clock per query, reported as p50 / p95 / p99. |
| **Per-query cost** | Token/compute cost per query (free-tier token accounting). |

All metrics are reported **with the single-LLM baseline alongside**, so every
number is a comparison, not an absolute in a vacuum.

## 4. Datasets

Public, citable factuality / hallucination benchmarks are used. Candidates under
evaluation (final selection and citations recorded in Phase 3):

- **HaluEval** — large-scale hallucination evaluation samples.
- **FACTS-style grounding sets** — answer-grounded-in-source judgements.

Selection criteria: free to obtain, redistributable or scriptable to download,
well-cited, and aligned with claim-level grounded verification.

These benchmark datasets supply the *claims and gold labels*; the *evidence* the
system grounds in is the fixed medical corpus described in §5 (Fixed-corpus
benchmarking). The two are distinct: the corpus is what the Retriever searches, the
datasets are what the verdicts are scored against.

## 5. Experimental protocol

- **Non-determinism handling.** Each configuration is run multiple times with
  fixed seeds where supported; results report mean ± standard deviation.
- **Apples-to-apples baseline.** The single-LLM baseline uses the same model,
  prompt budget, and corpus access policy as the multi-agent system, differing
  only in the verification architecture.
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

| System | Catch rate | False-flag rate | Accuracy |
| --- | --- | --- | --- |
| Single-LLM baseline | _live run_ | _live run_ | _live run_ |
| Aletheia (grounded verifier) | _live run_ | _live run_ | _live run_ |

> Numbers are produced by the live run on the author's free-tier key and recorded
> here once captured. The hypothesis under test is that the grounded verifier's
> catch rate exceeds the baseline's on the planted claims, at a modest false-flag
> cost.

### 6.2 Phase 3 — headline benchmark

_Pending Phase 3._ The headline table will take the following shape:

| System | Verif. accuracy | Catch rate | False-agreement | Latency p50/p95/p99 | Cost/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | — | — | — | — | — |
| Aletheia (grounded multi-agent) | — | — | — | — | — |

Per-dataset breakdowns, ablations (e.g., grounding on/off), and error analysis
will accompany the headline table.

## 7. Threats to validity

- **Benchmark leakage / contamination** into pretraining — mitigated by reporting
  the *relative* gap to the baseline rather than absolute scores.
- **Prompt sensitivity** — controlled by holding prompts fixed across systems and
  reporting variance across runs.
- **Retriever ceiling** — verification can only ground in what is retrievable;
  retrieval quality is measured and reported separately.

## 8. Novelty claim (to be validated)

Most prior work performs *either* hallucination detection *or* natural-language
agent debate. Aletheia's contribution is **evidence-grounded verification**
(every verdict cites source text) inside a **deployed, evaluated, multi-agent
system** with a **reusable evaluation harness**. The precise claim is checked
against current literature in Phase 3 and refined here with citations.
