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
_SciFact · 100 claims · seed 7 · 1 seeded run · groq:llama-3.1-8b-instant · corpus coverage 100.0% · 2026-07-19 · mean ± std._

| System | Verif. accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 60.0% ± 0.0% | 60.3% ± 0.0% | 37.7% ± 0.0% | 0.301 / 8.928 / 12.945 | 1388.0 |
| Multi-agent, ungrounded (ablation) | 65.0% ± 0.0% | 65.5% ± 0.0% | 35.7% ± 0.0% | 14.058 / 18.998 / 21.657 | 1473.2 |
| Aletheia (grounded verifier) | 69.0% ± 0.0% | 82.8% ± 0.0% | 23.8% ± 0.0% | 0.409 / 0.565 / 1.108 | 1675.6 |

_Grounded vs baseline (H1) (paired, n=100): accuracy McNemar exact p = 0.163 (33 discordant); catch-rate Δ +22.4 pp, 95% CI [+12.1, +33.3]; false-agreement Δ -13.9 pp, 95% CI [-23.9, -5.0]._
_Grounded vs ungrounded ablation (H2) (paired, n=100): accuracy McNemar exact p = 0.523 (22 discordant); catch-rate Δ +17.2 pp, 95% CI [+8.1, +27.6]; false-agreement Δ -11.9 pp, 95% CI [-21.3, -3.8]._
_Significance computed on the first repeat's paired per-claim predictions; percentile bootstrap with 10,000 resamples, seed 7._
<!-- PHASE3:END -->

**Run provenance (2026-07-19, definitive re-validation with the improved verifier).** All
three systems judge the *same* claim against the *same* evidence, retrieved by hybrid
search over the **full SciFact corpus (5,183 abstracts, 15,411 chunks)** ingested into
pgvector. Claims are a **seeded (seed 7), gold-label-stratified sample of 100** from the
SciFact `dev` split (42 Supported / 21 Contradicted / 37 Unverifiable), and every cited
abstract is present in the corpus (coverage 100%). Model: **Groq `llama-3.1-8b-instant`**
for *all three* arms — the grounded verifier, the ungrounded multi-agent ablation, and the
single-LLM baseline — so every comparison is apples-to-apples; the 8B model is used because
the larger models' free-tier **daily token caps** do not survive a sweep this size. This run
uses the **two-sided span-sufficiency verifier prompt** (§6.5), the same one held out on a
preliminary n≈30 sample; this is its first n=100 headline run. A single seeded repeat is
reported, so the ± is 0.0; the harness supports `--repeats N` for mean ± std once budget
allows. These are **free-tier-bounded** numbers on an 8B model — a defensible signal, not a
final benchmark.

**What the result says — and what it does not.** The primary thesis metric holds under
paired significance, and by a wider margin than before: the grounded verifier **catches
meaningfully more hallucinations than the single-LLM baseline** — catch rate **82.8% vs
60.3%, Δ +22.4 pp with a 95% CI of [+12.1, +33.3] that excludes zero**. The ablation orders
exactly as the thesis predicts, single-LLM < ungrounded multi-agent < grounded (catch
60.3% → 65.5% → 82.8%), and grounding adds a further +17.2 pp of catch over the ungrounded
multi-agent arm (95% CI [+8.1, +27.6], also excluding zero).

Unlike the earlier (preliminary-verifier) run, **aggregate verification accuracy now
improves too** (grounded 69.0% vs baseline 60.0%, +9.0 pp) — though the McNemar test on
this comparison is not itself significant at n=100 (p = 0.163, 33 discordant pairs), so
read the accuracy gain as directionally consistent with the §6.5 preliminary result, not
as its own independently-significant finding. The verifier-improvement mechanism behaves
exactly as §6.5 predicted: §6.3's error analysis (regenerated against this run) shows
false-grounding on `Unverifiable` claims roughly halved (21 → 10 of 37) and verifier
abstention rose only modestly (11 → 14), a favorable trade that lifts both catch rate and
accuracy together. False-agreement also improved, now significantly: 23.8% vs 37.7%
baseline (Δ -13.9 pp, 95% CI [-23.9, -5.0]). The grounded run costs **~21% more tokens**
(1675.6 vs 1388/query) for a much *lower* latency than the earlier run (p50 0.409s vs
14.5s) — reflecting the removal of a redundant call path, not a benchmark artifact. In
short: at 8B and n=100, the improved verifier **turns grounding's hallucination-catch
advantage into a larger, still-significant gain, while also lifting aggregate accuracy for
the first time** — the definitive re-validation the plan called for. This is now the
paper's headline result; the §6.4 cross-model robustness study still reflects the
*previous* verifier version and is a candidate for its own re-check.

### 6.3 Error analysis — where the grounded arm's accuracy goes

Regenerated against the §6.2 definitive re-validation run (2026-07-19, improved verifier).
The analysis below joins the run's grounded traces (`runs/scifact.jsonl`) back to the
SciFact gold labels and tags every one of the 100 scored claims by outcome. It is pure,
offline, and reproducible — it calls no model or database, and it reproduces the 69.0%
grounded accuracy of §6.2 exactly, confirming the join:

    make error-analysis   # python -m aletheia.evaluation.error_analysis --claims \
                          # data/scifact/claims_dev.jsonl --sample 100 --seed 7 \
                          # --traces runs/scifact.jsonl

| Outcome | Claims | Share |
| --- | ---: | ---: |
| Correct | 69 | 69.0% |
| Retrieval miss (cited abstract not retrieved → Unverifiable) | 1 | 1.0% |
| Verifier abstention (evidence present, no span quoted) | 14 | 14.0% |
| Wrong direction (Supported ↔ Contradicted) | 6 | 6.0% |
| False grounding (gold Unverifiable, verdict asserts) | 10 | 10.0% |

| Gold label | n | Correct | retrieval_miss | verifier_abstention | wrong_direction | false_grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Supported | 42 | 32 | 0 | 8 | 2 | 0 |
| Contradicted | 21 | 10 | 1 | 6 | 4 | 0 |
| Unverifiable | 37 | 27 | 0 | 0 | 0 | 10 |

**Three things this decomposition establishes.** *First, retrieval is still not the
bottleneck:* only 1 of 100 gold-cited abstracts failed to reach the verifier, consistent
with the near-100% corpus coverage — errors are overwhelmingly verifier decisions, not
missing-evidence artefacts. *Second, the improved verifier prompt did exactly what §6.5
predicted — it shrank the false-grounding bucket:* over-assertion on NotEnoughInfo claims
fell from 21/37 to 10/37, while verifier abstention on answerable claims rose only
modestly (11 → 14). That trade is favorable — it costs a handful of genuine
Supported/Contradicted calls but recovers roughly twice as many false-grounding errors,
which is why aggregate accuracy improved this time instead of staying flat. *Third,
substantive disagreement dropped too:* wrong-direction flips fell from 10 to 6.

**Honest caveat on `false_grounding`.** SciFact's NotEnoughInfo label is defined against its
*annotated* evidence set, whereas Aletheia retrieves from the full frozen corpus — so a
verdict counted here as a false grounding is sometimes a genuinely-supported claim whose
evidence the SciFact annotators simply did not cite. The 10 figure is therefore an *upper
bound* on verifier error for this class, not a clean count of hallucinated grounding;
separating the two needs manual adjudication (Phase 6).

**What this predicts for the stronger-model run.** The dominant remaining sink — the 14
verifier-abstention cases — is where a more capable verifier's better span-sufficiency
judgement should help next; §6.4's cross-model study was run against the *previous*
verifier version, so its cross-scale conclusions (the accuracy sign-flip in particular)
are a candidate for re-checking against this improved prompt.
Per-dataset breakdowns will accompany it in Phase 6.

### 6.4 Cross-model robustness (exploratory, small-n)

The headline (§6.2) and its error analysis (§6.3) are on a single 8B model. To check
whether the findings are an artefact of that model, we re-ran the H1 comparison (baseline
vs grounded verifier, same frozen corpus) at three model scales on **identical seeded
claim samples**. Free-tier request/token caps bound the sizes hard, so these are **small
and every delta is statistically insignificant** — an exploratory robustness probe, read
for *direction and mechanism*, not as a headline. Two paired comparisons were affordable:
8B vs 70B on the same 30 claims, and 8B vs a 550B model on the same 19 (one item excluded
by a transient provider error in both arms). Models: Groq `llama-3.1-8b-instant` and
`llama-3.3-70b-versatile`; OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free`.

_Grounded verifier vs single-LLM baseline, by base-model scale (seed 7; grounded − baseline):_

| Base model | n | Baseline acc | Grounded acc | Δ acc | Δ catch | Δ false-agree |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `llama-3.1-8b-instant` | 30 | 56.7% | 66.7% | **+10.0** | +17.6 | −11.9 |
| `llama-3.1-8b-instant` | 19 | 63.2% | 68.4% | **+5.2** | +30.0 | −15.7 |
| `llama-3.3-70b-versatile` | 30 | 80.0% | 70.0% | **−10.0** | +5.9 | −6.0 |
| `nemotron-3-ultra-550b` | 19 | 89.5% | 73.7% | **−15.8** | +0.0 | +0.0 |

_Grounded-arm error mix (share of misses), same runs, via `make error-analysis`:_

| Base model | n | Grounded acc | Retrieval miss | False-grounding (of NEI) | Abstention (of answerable) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `llama-3.1-8b-instant` (§6.3) | 100 | 58.0% | 0 | 21/37 (57%) | 11/63 (17%) |
| `llama-3.3-70b-versatile` | 30 | 70.0% | 0 | 4/11 (36%) | 5/19 (26%) |
| `nemotron-3-ultra-550b` | 19 | 73.7% | 0 | 1/6 (17%) | 4/13 (31%) |

**Three things hold across scale.** *First, grounding's core value is robust:* wherever the
baseline leaves room, the grounded verifier catches more (catch Δ +5.9 to +30.0) and agrees
wrongly less (false-agreement Δ −6.0 to −15.7). At 550B the baseline already scores 100%
catch and 0% false-agreement, so there is nothing to improve and grounding simply matches
it. *Second, retrieval is never the bottleneck* — zero retrieval misses at every scale, so
every error is a verifier decision. *Third, false-grounding on NotEnoughInfo claims falls
monotonically as the model strengthens* (57% → 36% → 17% of NEI claims), exactly the
span-sufficiency improvement §6.3 predicted a better verifier would make.

**But grounding's accuracy effect flips sign with base-model strength.** Δ accuracy runs
+10.0 (8B) → −10.0 (70B) → −15.8 (550B): grounding *corrects* a weak model but *costs* a
strong one. The mechanism is visible in the error mix — as false-grounding shrinks with
scale, the residual error shifts to **over-abstention**: a capable model that would label a
claim correctly on its own is instead forced to `Unverifiable` when it cannot isolate a
single verbatim span (at 550B, 4 of 5 misses are abstentions on answerable claims). The
strict single-span discipline is a net win on accuracy only when the base model is weak
enough to need the correction.

**Caveats (binding).** n = 19–30, so every delta above is *not significant* (bootstrap CIs
touch or cross zero); the two comparisons use different, non-nested samples; the 550B model
is a free reasoning model with high tail latency (p95 ≈ 42–60 s) suitable for offline
evaluation only; and `false_grounding` remains an upper bound (open-corpus retrieval, §6.3).
These runs motivate the verifier-improvement work that follows: the accuracy cost is
concentrated in two span-judgement failures — false-grounding at weak models, over-abstention
at strong ones — both of which the Verifier prompt can target directly.

### 6.5 Verifier improvement — the span-sufficiency test (preliminary)

Both failure modes §6.3–§6.4 localise are the *same* underlying decision: does the quoted
span actually **settle** this claim, or does it merely touch its topic? Under-answering
that question produces false-grounding (asserting on a topical span); over-answering it
produces abstention (refusing a span that plainly decides the claim). So the Verifier
prompt was given an explicit, two-sided **span-sufficiency test**: assert `Supported` /
`Contradicted` only when the span, read alone, directly decides the claim; do *not* retreat
to `Unverifiable` when it plainly does; and treat a merely-topical or background span as
`Unverifiable`. The change is **additive to the verdict contract** (verdict + span +
reasoning, unchanged) and lives only in the grounded prompt, so the H2 ablation's fairness
contract is preserved (a guard test, `tests/agents/test_prompts.py`, pins this). It was
derived from the *aggregate* error taxonomy, not from any per-item inspection.

It was A/B-tested on the 8B model with everything else fixed — same claims, same corpus,
temperature 0 — so the single-LLM baseline arm is an unchanged control. The decisive test
is a **held-out sample (seed 13) the change was not informed by**:

| Grounded arm (8B) | Sample | Accuracy | Catch | False-agreement |
| --- | --- | ---: | ---: | ---: |
| Old verifier | seed 13 (held-out, n=30) | 53.3% | 76.5% | 28.6% |
| **New verifier** | seed 13 (held-out, n=30) | **66.7%** | 76.5% | 26.7% |
| Old verifier | seed 7 (n≈30) | 66.7% | 82.4% | 21.4% |
| **New verifier** | seed 7 (n≈30) | **72.4%** | 81.2% | 21.4% |

On the held-out sample the sufficiency test lifts grounded **accuracy +13.4 pp (53.3 → 66.7)
with catch-rate unchanged (76.5)** and false-agreement slightly lower — flipping the
grounded arm from 10 pp *below* the single-LLM baseline to 3.4 pp *above* it (the baseline
is identical, 63.3%, in both runs). The error analysis confirms the intended mechanism:
correct 16 → 20, with **false-grounding 8 → 6 and abstention 4 → 2** — both targeted modes
fall, nothing is traded away on catch. The seed-7 sample moves the same direction (+5.7 pp
accuracy, catch flat).

**This is a preliminary, honest signal — not yet a headline.** The samples are n≈30 and the
accuracy gains are **not statistically significant** at that size; the A/B is on the 8B
model only; and the change was validated against the OLD verifier, not yet re-run at the
§6.2 scale. The §6.2 headline table therefore still reports the pre-improvement verifier.
The definitive test — regenerating the n=100 headline with the improved verifier, and
re-checking the §6.4 strong models (where the failure was over-abstention) — is a
fresh-free-tier-quota run; if the +13 pp held-out gain holds at n=100 it becomes the
headline, and if it shrinks that will be reported plainly.

#### Re-check at larger scales: the gain does not carry up — it sharpens the trade-off

The §6.4 strong models were re-run with the improved verifier on the same seeded samples
(2-arm H1, seed 7, fallbacks disabled so no provider mixing; the unchanged baseline arm is
the control). The 70B comparison is a clean A/B — its baseline reproduces exactly (80.0%
accuracy in both runs). The 550B comparison is **not**: one item of the old run had been
dropped by a transient provider error (n=19 vs n=20) and the baseline itself moved
(89.5% → 75.0%), so its delta is sample drift, not a verifier effect, and it is reported
only for completeness.

_Grounded arm, old → new verifier (same seed-7 samples; baseline in parentheses):_

| Base model | n | Accuracy | Catch | False-agreement |
| --- | ---: | --- | --- | --- |
| `llama-3.3-70b-versatile` (80.0%) | 30 | 70.0% → **66.7%** | 94.1% → **100.0%** | 8.3% → **0.0%** |
| `nemotron-3-ultra-550b` (89.5% → 75.0%) | 19→20 | 73.7% → 70.0% | 100.0% → 100.0% | 0.0% → 0.0% |

_70B grounded-arm error mix, old → new (via `make error-analysis`):_ false-grounding on
NotEnoughInfo claims **4/11 → 2/11**, verifier abstention on answerable claims
**5/19 → 7/19** (plus one retrieval-tagged miss).

**Reading.** At 70B the sufficiency test does exactly what it was written to do — it halves
false-grounding — but its "do not retreat from a decisive span" side does not hold on a
strong model: abstention rises more than false-grounding falls, so accuracy slips 3.3 pp
while catch reaches 100% and false-agreement reaches zero. In other words, the improvement
**sharpens the §6.4 trade-off rather than escaping it**: on a weak model it buys accuracy,
catch, and false-agreement together (§6.5 above); on a strong model it pushes the grounded
arm further toward maximum catch and zero false-agreement *at* accuracy cost. The
span-sufficiency gain is therefore an **8B-scale result, stated as such** — consistent with
§6.4's conclusion that strict span grounding is a net accuracy win only where the base
model needs the correction, while its catch/false-agreement advantages hold at every scale.

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
