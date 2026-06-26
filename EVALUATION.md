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

## 6. Results

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
