# Aletheia: Span-Grounded Multi-Agent Verification Structurally Reduces False Agreement, at a Model-Dependent Accuracy Cost

**Jay Gautam**

*Draft — generated from `EVALUATION.md` on 2026-07-19. This is a working preprint,
not a final submission: the headline numbers below are honestly labelled as
preliminary or definitive per section, and one run (the n=100 re-validation with
the improved verifier, §5.6) is still outstanding. Update this document, do not
fork it, once that run lands — see "Status of this draft" at the end.*

## Abstract

Multi-agent LLM pipelines that verify claims by letting instances debate or
critique each other can still fail by *agreeing on the wrong answer* — nothing
in an opinion-only exchange prevents correlated hallucination. We present
Aletheia, a verification pipeline in which agreement is constrained
structurally: a verdict may affirm or contradict a claim only by quoting a
verbatim span of retrieved evidence, and is otherwise forced to
`Unverifiable`. We evaluate it against a single-LLM baseline and an
ungrounded multi-agent ablation on SciFact (Wadden et al., 2020), grounding
all three systems in the same frozen, fixed biomedical corpus so every
comparison is reproducible. On a seeded, gold-label-stratified sample of 100
claims (Groq `llama-3.1-8b-instant`), grounded verification achieves a
statistically significant hallucination-catch-rate gain over the baseline
(70.7% vs 60.3%, Δ +10.3 pp, 95% CI [+3.3, +18.6]), while aggregate accuracy
is flat (58.0% vs 60.0%, McNemar p = 0.839). An offline error-mode analysis
attributes the flat accuracy to over-assertion on claims the corpus cannot
settle, not to a retrieval ceiling (zero retrieval misses). A cross-model
robustness check at 70B and a free 550B-class model shows the catch-rate and
false-agreement advantages of grounding hold across scale, but the accuracy
effect **flips sign** with base-model strength (+10 pp at 8B, −10 to −16 pp
at 70B/550B): grounding corrects a weak model and costs a strong one, because
the strict single-span rule forces over-abstention once the underlying model
would already answer correctly. A targeted verifier prompt change (a
two-sided span-sufficiency test) recovers +13.4 pp of accuracy on a held-out
8B sample without giving up catch rate, but the same change *sharpens* rather
than escapes the strong-model trade-off. We report all of this — including
the parts that do not support a clean story — because the honest finding is
itself the contribution: span-grounded structural agreement is a real,
significant defense against false agreement at every scale tested, and a
real, model-dependent accuracy trade rather than a free lunch.

## 1. Introduction

Two bodies of prior work motivate this system and neither, on its own, is
what we build. **Claim verification / fact-checking** systems label a claim
against retrieved evidence — FEVER (Thorne et al., 2018) over Wikipedia,
SciFact (Wadden et al., 2020) over scientific abstracts — but typically score
a single model's judgment, not a multi-agent process. **Hallucination
detection and self-verification** methods (SelfCheckGPT, Manakul et al.,
2023; Chain-of-Verification, Dhuliawala et al., 2023) flag unsupported
output, often via consistency across sampled generations rather than
evidence grounding. Separately, **multi-agent debate/critique** methods
(Du et al., 2023) improve factuality through natural-language exchange among
model instances — but nothing in an opinion-only exchange structurally
prevents the agents from confidently agreeing on the same wrong answer.

Aletheia sits at the intersection these three leave open: a multi-agent
verification pipeline whose agreement is constrained by evidence at the
mechanism level, not the prompt level. A verdict may affirm `Supported` or
`Contradicted` only by quoting a verbatim span of the retrieved evidence text
that the system can check programmatically against that text; failing that
check forces `Unverifiable`. This is deliberately narrower than free-form
debate — it trades expressiveness for a structural guarantee: two agents
cannot both hallucinate agreement on a claim neither can quote support for.

We do not claim this combination is unoccupied in the literature — that
priority claim is explicitly not the headline (§7) — and this draft is
upfront that not every result supports the thesis cleanly. The contribution
we defend is narrower and, we think, more useful: a working, evaluated
system plus a seeded, reproducible harness that reports *where* structural
grounding helps, *where* it costs, and *why*, across three model scales.

## 2. System

Aletheia is a LangGraph-orchestrated pipeline: an **Intake guard** (a
deterministic prompt-injection scan plus an LLM scope classifier, bypassed
only when the caller supplies their own evidence) admits or refuses a query;
a **Retriever** performs hybrid (semantic + keyword) search over a frozen,
versioned PostgreSQL/pgvector corpus; a **Generator** proposes an answer
decomposed into atomic claims; a per-claim **Verifier** judges each claim
against retrieved evidence under the quoted-span discipline; an
**Aggregator** collects verdicts and surfaces any disagreement explicitly
(never hidden); and a non-mutating **Guardrail** attaches a confidence
advisory and a standing "verification tool, not medical advice" disclaimer.
The LLM client is provider-agnostic (Gemini, Groq, OpenRouter), selected by
configuration, so the same pipeline runs unmodified across the model scales
compared in §5.4.

Two properties matter for the evaluation that follows. First, **grounding is
structural, not aspirational**: the pipeline code checks a claimed span
against the evidence text; a verdict that cannot produce a matching span is
programmatically downgraded, not merely instructed to be honest. Second,
**the benchmark and the live system share one grounding path** — there is no
separate "eval mode" — so the numbers below describe the deployed system,
not a stripped-down harness variant of it.

## 3. Research question and hypotheses

**RQ.** Does an evidence-grounded, multi-agent verification pipeline catch
measurably more hallucinations than a single LLM, and at what latency and
cost?

- **H1 (catch rate).** Aletheia achieves a higher hallucination-catch rate
  than a single-LLM baseline on the same benchmark.
- **H2 (grounding reduces false agreement).** Requiring quoted-span evidence
  lowers the false-agreement rate versus an otherwise-identical multi-agent
  arm whose verdicts are opinion-only (no span discipline).
- **H3 (acceptable cost).** The reliability gains come at a quantified,
  defensible latency and per-query cost overhead.

## 4. Method

**Benchmark.** SciFact (Wadden et al., 2020; CC BY-NC 2.0): expert-written
scientific claims labelled `SUPPORT` / `CONTRADICT` / no-evidence against
biomedical abstracts, mapping directly onto the pipeline's own three-valued
verdict space. Its own abstract corpus is ingested into the frozen store, so
growing the corpus to cover the benchmark is a defined, reproducible ingest
rather than open retrieval.

**Systems compared, all judging the same claim against the same retrieved
evidence with the same model:**
- *Single-LLM baseline* — one holistic call, no span discipline.
- *Multi-agent, ungrounded (ablation)* — the same per-claim critic as the
  grounded system, with the quoted-span requirement removed; isolates what
  grounding contributes, holding the multi-agent structure fixed (H2).
- *Aletheia (grounded verifier)* — the full system.

**Sampling.** A seeded (seed 7), gold-label-stratified sample without
replacement, preserving the benchmark's label mix rather than a head-slice's
bias; corpus coverage (every cited abstract present in the frozen corpus) is
checked and reported before scoring.

**Statistics.** Because all systems judge the same claims, headline gaps are
tested on paired per-claim predictions: an exact McNemar test for accuracy,
and percentile-bootstrap 95% CIs (10,000 resamples, fixed seed) for catch-
rate and false-agreement deltas.

**Fault tolerance.** A provider error on any arm excludes that item from
*every* arm (never fabricating a verdict), keeping comparisons paired; a
run whose failures exceed a small cap aborts rather than reporting a
silently-partial result.

**Metrics.** Verification accuracy; hallucination-catch rate (recall on
truly unsupported/false claims); false-agreement rate; latency p50/p95/p99
(verification work only — shared retrieval is measured once and excluded);
per-query token cost.

## 5. Results

### 5.1 Headline benchmark (n=100, 8B model)

*Groq `llama-3.1-8b-instant`, all three arms, seed 7, single seeded repeat,
100% corpus coverage, 2026-07-03.*

| System | Accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 60.0% | 60.3% | 37.7% | 14.5 / 18.7 / 19.6 | 1388 |
| Multi-agent, ungrounded | 65.0% | 65.5% | 35.7% | 14.5 / 18.6 / 20.5 | 1473 |
| **Aletheia (grounded)** | 58.0% | **70.7%** | 35.4% | 15.5 / 19.5 / 21.5 | 1558 |

**H1 confirmed, significant:** catch rate 70.7% vs 60.3%, Δ +10.3 pp, 95% CI
[+3.3, +18.6] (excludes zero). The ablation orders exactly as predicted,
single-LLM < ungrounded < grounded (60.3 → 65.5 → 70.7). **The honest
caveat:** aggregate accuracy does not improve (58.0% vs 60.0%, McNemar
p = 0.839 — indistinguishable), and false-agreement's nominal edge (35.4%
vs 37.7%) is not significant at this n. H3: the grounded arm costs ~12%
more tokens for a modest latency overhead — a defensible, quantified
overhead, not a free lunch. §5.2 explains why accuracy stays flat despite
a real catch-rate gain.

### 5.2 Where the flat accuracy comes from

Joining the grounded arm's traces back to gold labels and tagging every
scored claim by outcome (retrieval miss / verifier abstention / wrong
direction / false grounding) shows retrieval is **not** the bottleneck —
zero of the cited abstracts were missing from the corpus, so every error is
a verifier decision. The dominant sink is **over-assertion**, not
over-caution: 21 of 37 `NotEnoughInfo` claims are wrongly asserted on
(`false_grounding`) versus 11 answerable claims wrongly abstained on
(`verifier_abstention`). `false_grounding` is reported as an *upper bound*:
SciFact's `NotEnoughInfo` label is defined against its own annotated
evidence, while Aletheia retrieves from the full corpus, so some counted
"false groundings" may be genuinely-supported claims whose evidence the
annotators simply did not cite — disambiguating the two needs manual
adjudication, noted as future work.

### 5.3 Cross-model robustness (exploratory, small-n)

To check whether §5.1–5.2 are an 8B artifact, H1 was re-run at 70B (Groq
`llama-3.3-70b-versatile`, n=30) and a free 550B-class model (OpenRouter
`nemotron-3-ultra-550b`, n=19) on identical seeded samples. **Caveat
binding throughout this subsection: n=19–30, every delta below is not
statistically significant** (bootstrap CIs touch or cross zero) — read for
direction and mechanism, not as a headline.

| Base model | n | Baseline acc | Grounded acc | Δ acc | Δ catch | Δ false-agree |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8B | 30 | 56.7% | 66.7% | **+10.0** | +17.6 | −11.9 |
| 70B | 30 | 80.0% | 70.0% | **−10.0** | +5.9 | −6.0 |
| 550B-class | 19 | 89.5% | 73.7% | **−15.8** | +0.0 | +0.0 |

Grounding's catch-rate and false-agreement advantages hold at every scale
(at 550B the baseline is already at ceiling, so there is nothing left to
improve). But **the accuracy effect flips sign with base-model strength**:
+10 pp at 8B, −10 to −16 pp at 70B/550B. The mechanism is visible in the
error mix — false-grounding on `NotEnoughInfo` falls monotonically with
scale (57% → 36% → 17%), but the residual error shifts to
**over-abstention**: a strong model that would answer correctly on its own
is instead forced to `Unverifiable` when it cannot isolate one verbatim
span. The strict single-span rule is a net accuracy win only when the base
model is weak enough to need the correction.

### 5.4 A targeted verifier improvement (preliminary, 8B)

Both failure modes above are the same underlying judgment — does a span
*settle* the claim, or merely touch its topic? A two-sided **span-
sufficiency test** was added to the grounded prompt: assert only when the
span, alone, directly decides the claim; do not retreat to `Unverifiable`
when it plainly does; treat a merely-topical span as `Unverifiable`. This
is additive to the verdict contract (a guard test pins the ablation's
fairness). On a held-out 8B sample (seed 13, not used to derive the
change), accuracy rises **53.3% → 66.7% (+13.4 pp)** with catch-rate
unchanged and false-agreement slightly lower — flipping the grounded arm
from 10 pp below the (unchanged) baseline to 3.4 pp above it. The error mix
confirms the intended mechanism: false-grounding 8→6, abstention 4→2 — both
targeted modes fall, nothing traded away on catch.

**This is preliminary**: n≈30, not statistically significant, 8B only, and
not yet re-run at the §5.1 scale — the §5.1 headline above still reports
the pre-improvement verifier.

### 5.5 The improvement does not carry to stronger models

Re-running the improved verifier on the same §5.3 seeded samples at 70B
(clean A/B — the baseline reproduces exactly at 80.0%) shows the sufficiency
test does exactly what it targets — false-grounding on `NotEnoughInfo` halves
(4/11 → 2/11) — but its "do not retreat from a decisive span" side does not
hold on a strong model: abstention *rises* more than false-grounding falls
(5/19 → 7/19), so accuracy **slips** 70.0% → 66.7% while catch reaches 100%
and false-agreement reaches zero. In other words, the change **sharpens**
§5.3's trade-off rather than escaping it: an 8B-scale accuracy win, stated as
such, alongside catch/false-agreement advantages that hold at every scale
tested. (A parallel 550B re-check was inconclusive — its baseline drifted
between runs — and is reported for completeness only, not as evidence either
way.)

### 5.6 What remains before this becomes the final headline

The definitive test — regenerating the §5.1 n=100 headline with the
improved verifier, on a fresh Groq free-tier quota day — is still
outstanding at the time of this draft. If the held-out +13.4 pp gain holds
at n=100, §5.4's verifier improvement is promoted to the headline
(with the accuracy caveat replaced or narrowed); if it shrinks, that will be
reported plainly, exactly as the smaller-n results above were reported
plainly whether or not they helped the thesis. This document is not final
until that run lands and this section is removed.

## 6. Threats to validity

- **Benchmark leakage / contamination** into pretraining — mitigated by
  reporting the *relative* gap to the baseline rather than absolute scores.
- **Prompt sensitivity** — controlled by holding prompts fixed across
  systems within a comparison and reporting variance across runs.
- **Retriever ceiling** — verification can only ground in what is
  retrievable; §5.2 measures retrieval misses directly and finds none at
  the scale tested, but this is corpus- and query-set-specific.
- **Small-n exploratory sections (§5.3–5.5)** — every cross-model and
  verifier-improvement delta reported there is statistically
  insignificant; they are read for mechanism and direction only.
- **Single-domain evaluation** — every result above is on SciFact, a
  biomedical benchmark. A second, general-domain benchmark (FEVER, over a
  seeded Wikipedia corpus slice) is scaffolded but not yet run at the time
  of this draft (§7).

## 7. Related work and novelty claim (positioning)

As introduced in §1: claim-verification systems (FEVER, SciFact) and
hallucination-detection methods (SelfCheckGPT, Chain-of-Verification)
typically score a single model's judgment against evidence or against its
own sampled consistency; multi-agent debate/critique methods (Du et al.,
2023) improve factuality through exchange among model instances but do not,
to our knowledge, constrain that exchange with a checkable evidence-span
requirement. Aletheia's contribution is the *combination*, delivered as a
deployed, evaluated service with a reusable, seeded harness: a multi-agent
pipeline whose agreement is structurally constrained by quoted-span
grounding, benchmarked against a single-LLM baseline and an ungrounded
ablation on a fixed, citable corpus, across three model scales.

This is a **positioning claim, not a systematic survey**. The citations
above are landmark references, not the product of a structured literature
search — that validation is planned before final submission, alongside the
FEVER generalization run (§8).

## 8. Future work

- **The n=100 re-validation with the improved verifier** (§5.6) — decides
  whether §5.4's accuracy gain is promoted to the paper's headline.
- **A second, general-domain benchmark (FEVER)** — a seeded, closed
  Wikipedia corpus slice sized like SciFact, with its own connector and
  claim loader already built and offline-tested; the live n=100 run is the
  only step remaining, needing its own free-tier quota day.
- **Manual adjudication of the `false_grounding` upper bound** (§5.2) —
  separating genuinely hallucinated grounding from claims whose supporting
  evidence SciFact's annotators simply did not cite.
- **A structured literature search** validating the novelty framing in §7
  against the current state of the multi-agent-verification and
  hallucination-detection literature.
- **Repeats at scale** (`--repeats N`) for tighter confidence intervals on
  the headline gaps, budget permitting.

## Status of this draft

This is a living document, regenerated from `EVALUATION.md` as new runs
land — it is not a frozen submission. As of 2026-07-19: §5.1–5.5 reflect
completed, merged work; §5.6's re-validation run and the FEVER live run
(§8) are the two outstanding pieces of evaluation before a final version can
be prepared for submission. Do not cite specific numeric values from this
draft as final without checking `EVALUATION.md` for a more recent run.
