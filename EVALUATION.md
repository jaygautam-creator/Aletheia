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
- **Sampling.** When a run uses a subset of the benchmark (`--sample N`), the
  subset is drawn by **seeded, gold-label-stratified sampling** without
  replacement: allocation is proportional to each label's share of the full
  claim set, so the sample preserves the Supported/Contradicted/Unverifiable
  mix rather than the bias of a head-slice, and the same `(claims, N, seed)`
  always reproduces the same subset. Before any model is called, the runner
  checks **corpus coverage** — the fraction of sampled claims whose every cited
  abstract is present in the frozen corpus — and warns loudly below 95%, since
  a claim with missing evidence can only come back Unverifiable. The generated
  §6.2 caption records n, seed, repeats, model, coverage, and the run date.
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
- **Fault tolerance without bias.** A provider error on one item excludes that
  item from **every** arm — a verdict is never fabricated for a failed call —
  so all comparisons stay paired. Failures are named in the run summary and any
  failure makes the run exit non-zero (a partial run cannot pass silently as
  complete); more than a small cap (`--max-failures`, default 5) aborts the
  run with partial traces written.
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
_SciFact · 100 claims · seed 7 · 1 seeded run · groq:llama-3.1-8b-instant · corpus coverage 100.0% · 2026-07-03 · mean ± std._

| System | Verif. accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 60.0% ± 0.0% | 60.3% ± 0.0% | 37.7% ± 0.0% | 14.540 / 18.692 / 19.595 | 1388.0 |
| Multi-agent, ungrounded (ablation) | 65.0% ± 0.0% | 65.5% ± 0.0% | 35.7% ± 0.0% | 14.505 / 18.570 / 20.519 | 1472.8 |
| Aletheia (grounded verifier) | 58.0% ± 0.0% | 70.7% ± 0.0% | 35.4% ± 0.0% | 15.480 / 19.535 / 21.478 | 1558.0 |

_Grounded vs baseline (H1) (paired, n=100): accuracy McNemar exact p = 0.839 (24 discordant); catch-rate Δ +10.3 pp, 95% CI [+3.3, +18.6]; false-agreement Δ -2.3 pp, 95% CI [-9.1, +3.9]._
_Grounded vs ungrounded ablation (H2) (paired, n=100): accuracy McNemar exact p = 0.118 (15 discordant); catch-rate Δ +5.2 pp, 95% CI [+0.0, +11.7]; false-agreement Δ -0.3 pp, 95% CI [-5.7, +4.7]._
_Significance computed on the first repeat's paired per-claim predictions; percentile bootstrap with 10,000 resamples, seed 7._
<!-- PHASE3:END -->

**Run provenance (2026-07-03).** All three systems judge the *same* claim against the
*same* evidence, retrieved by hybrid search over the **full SciFact corpus (5,183
abstracts, 15,411 chunks)** ingested into pgvector. Claims are a **seeded (seed 7),
gold-label-stratified sample of 100** from the SciFact `dev` split (42 Supported / 21
Contradicted / 37 Unverifiable), and every cited abstract is present in the corpus
(coverage 100%). Model: **Groq `llama-3.1-8b-instant`** for *all three* arms — the grounded
verifier, the ungrounded multi-agent ablation, and the single-LLM baseline — so every
comparison is apples-to-apples; the 8B model is used because the larger models' free-tier
**daily token caps** do not survive a sweep this size. A single seeded repeat is reported,
so the ± is 0.0; the harness supports `--repeats N` for mean ± std once budget allows.
These are **free-tier-bounded** numbers on an 8B model — a defensible signal, not a final
benchmark.

**What the result says — and what it does not.** The primary thesis metric holds under
paired significance: the grounded verifier **catches meaningfully more hallucinations than
the single-LLM baseline** — catch rate **70.7% vs 60.3%, Δ +10.3 pp with a 95% CI of
[+3.3, +18.6] that excludes zero**. The ablation orders exactly as the thesis predicts,
single-LLM < ungrounded multi-agent < grounded (catch 60.3% → 65.5% → 70.7%), and grounding
adds a further +5.2 pp of catch over the ungrounded multi-agent arm — though that gap's CI
lower bound touches 0.0, so it is suggestive rather than conclusive at n=100.

The honest caveat is that **aggregate verification accuracy does not improve** (grounded
58.0% vs baseline 60.0%; McNemar exact p = 0.839 — indistinguishable). The same quoted-span
discipline that catches more errors also **reshapes the mistakes the verifier makes**: at
8B it both downgrades some genuinely answerable claims to `Unverifiable` *and* over-asserts
on some claims the corpus cannot settle — §6.3 decomposes exactly where the accuracy goes,
and finds the second effect is the larger one. False-agreement is nominally lowest for the
grounded arm (35.4% vs 37.7%) but the difference is not significant at this n. The grounded
run costs **~12% more tokens** (1558 vs 1388/query) for a modest latency overhead. In
short: at 8B and n=100, grounding **buys a real, significant gain in hallucination-catch —
the metric the whole system exists to move — without a free lunch on aggregate accuracy.**
Scaling to seeded repeats and a stronger model, plus the error analysis in §6.3, is what
turns this signal into the paper's headline.

### 6.3 Error analysis — where the grounded arm's accuracy goes

A flat aggregate accuracy is only a defensible finding if we can say *which* claims the
grounded verifier gets wrong and *why*. The analysis below joins the run's grounded traces
(`runs/scifact.jsonl`) back to the SciFact gold labels and tags every one of the 100 scored
claims by outcome. It is pure, offline, and reproducible — it calls no model or database,
and it reproduces the 58.0% grounded accuracy of §6.2 exactly, confirming the join:

    make error-analysis   # python -m aletheia.evaluation.error_analysis --claims \
                          # data/scifact/claims_dev.jsonl --sample 100 --seed 7 \
                          # --traces runs/scifact.jsonl

| Outcome | Claims | Share |
| --- | ---: | ---: |
| Correct | 58 | 58.0% |
| Retrieval miss (cited abstract not retrieved → Unverifiable) | 0 | 0.0% |
| Verifier abstention (evidence present, no span quoted) | 11 | 11.0% |
| Wrong direction (Supported ↔ Contradicted) | 10 | 10.0% |
| False grounding (gold Unverifiable, verdict asserts) | 21 | 21.0% |

| Gold label | n | Correct | retrieval_miss | verifier_abstention | wrong_direction | false_grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Supported | 42 | 31 | 0 | 6 | 5 | 0 |
| Contradicted | 21 | 11 | 0 | 5 | 5 | 0 |
| Unverifiable | 37 | 16 | 0 | 0 | 0 | 21 |

**Three things this decomposition establishes.** *First, retrieval is not the bottleneck at
n=100:* every gold-cited abstract reached the verifier (0 retrieval misses), consistent with
the 100% corpus coverage — so every error above is a verifier decision, not a
missing-evidence artefact. *Second, the largest single accuracy sink is over-assertion, not
over-caution:* on 21 of 37 NotEnoughInfo claims the 8B verifier asserted a stance it should
have declined (`false_grounding`), against 11 answerable claims it wrongly abstained on
(`verifier_abstention`). This refines the §6.2 caveat — the quoted-span rule does cost some
genuine Supported/Contradicted verdicts, but at 8B the bigger leak is the verifier quoting a
*topically related* span that does not actually settle a claim the corpus cannot settle.
*Third, substantive disagreement is rare:* only 10 claims are outright direction flips.

**Honest caveat on `false_grounding`.** SciFact's NotEnoughInfo label is defined against its
*annotated* evidence set, whereas Aletheia retrieves from the full frozen corpus — so a
verdict counted here as a false grounding is sometimes a genuinely-supported claim whose
evidence the SciFact annotators simply did not cite. The 21 figure is therefore an *upper
bound* on verifier error for this class, not a clean count of hallucinated grounding;
separating the two needs manual adjudication (Phase 6).

**What this predicts for the stronger-model run.** The dominant sink — false grounding on
NotEnoughInfo claims — is precisely a *span-sufficiency judgement*: deciding whether a
retrieved span genuinely settles a claim or merely mentions its topic. That is where a more
capable verifier is expected to help most, so the stronger-model run (in progress) is the
direct test of whether shrinking this bucket lifts aggregate accuracy above the baseline.
Per-dataset breakdowns will accompany it in Phase 6.

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
