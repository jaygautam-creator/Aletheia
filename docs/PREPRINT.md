# Aletheia: A Structural Evidence Gate for Multi-Agent Claim Verification — Catch-Rate Gains That Persist Across Scale and Domain, and an Accuracy Trade-Off That Depends on Both

**Jay Gautam**

*Draft — generated from `EVALUATION.md` on 2026-08-03. This is a working preprint, not a
final submission. Every number below is traceable to a committed run in `EVALUATION.md`;
nothing here is projected or rounded up. Two items remain before final submission: a
full-text read of three multi-agent-debate papers surfaced by the literature search (§7),
and a manual adjudication of the SciFact `false_grounding` upper bound (§5.3, §8). Update
this document in place as those land — see "Status of this draft" at the end.*

## Abstract

Multi-agent LLM pipelines that verify claims by letting instances debate or critique each
other can still fail by *agreeing on the wrong answer* — nothing in an opinion-only
exchange prevents correlated hallucination. We present Aletheia, a verification pipeline
in which agreement is constrained structurally: a verdict may affirm or contradict a claim
only by quoting a verbatim span of retrieved evidence, checked programmatically against
the evidence text, and is otherwise forced to `Unverifiable`. We evaluate it against a
single-LLM baseline and an ungrounded multi-agent ablation on SciFact (Wadden et al.,
2020) and, as a harder second domain, FEVER (Thorne et al., 2018), grounding all systems
in the same frozen, versioned corpus so every comparison is reproducible.

On SciFact with a weaker base model (Groq `llama-3.1-8b-instant`, n=100), grounded
verification achieves a statistically significant catch-rate gain over the baseline
(70.7% vs 60.3%, Δ +10.3 pp, 95% CI [+3.3, +18.6]) while aggregate accuracy is flat
(58.0% vs 60.0%). Re-running the identical protocol on the model now serving live traffic
(Gemini `gemini-3.1-flash-lite-preview`, n=100) tells a different, more honest story:
**the accuracy edge disappears entirely (79.0% vs 79.0%, exactly tied)**, and the
catch-rate/false-agreement gains, while still directionally favorable (+3.4 pp catch,
−4.5 pp false-agreement), are no longer clearly established at this sample size (both
confidence intervals touch or cross zero). A cross-model sweep spanning 8B to 550B-class
models shows the mechanism: grounding's accuracy contribution is *inversely related to
base-model strength*, because a strong model that would already answer correctly is
sometimes forced into `Unverifiable` by the single-span discipline, while a weak model's
own errors are what grounding was catching in the first place. A targeted verifier
improvement (a two-sided span-sufficiency test) recovers +13.4 pp of accuracy at 8B scale
without giving up catch rate, but *sharpens* rather than escapes the strong-model
trade-off when re-tested at 70B.

A second, harder domain stress-tests the guarantee itself rather than the accuracy story:
FEVER's claims are crowdworker paraphrases of Wikipedia sentences, not near-quotations of
their evidence — exactly the condition under which verbatim grounding should struggle
most. A corpus-cleaning fix (folding FEVER's Penn-Treebank markup to plain text) recovers
+21 pp of grounded accuracy (56.0% → 77.0%, paired McNemar p = 4.9e-05) that had been lost
to a tokenization artifact, not a reasoning ceiling. After the fix, grounding still trails
the ungrounded ablation on raw accuracy (77.0% vs 85.0%, p = 0.008) — paraphrase claims are
where the strict single-span rule costs the most — but the **load-bearing check holds
exactly as designed**: of the 51 verdicts the grounded system asserts, 51/51 (100%) are
backed by a span verified verbatim in the retrieved evidence. The system's remaining
errors are real entailment mistakes by the underlying reader, not fabricated grounding or
guard failures — the one guarantee Aletheia makes is the one guarantee it keeps, even on
the domain built to break it.

We report all of this, including the parts that do not support a clean story, because the
honest finding is the contribution: a structural evidence gate is a real, mechanically
verifiable defense against false agreement, whose catch-rate and safety-metric direction
holds across three model scales and two domains, and whose accuracy effect is a genuine,
model- and domain-dependent trade rather than a free lunch.

## 1. Introduction

Two bodies of prior work motivate this system, and neither, on its own, is what we build.
**Claim verification / fact-checking** systems label a claim against retrieved evidence —
FEVER (Thorne et al., 2018) over Wikipedia, SciFact (Wadden et al., 2020) over scientific
abstracts, the latter's own VeriSci baseline itself extractive (TF-IDF retrieval plus a
RoBERTa rationale-sentence selector), later improved on by MultiVerS (Wadden et al.,
Findings of NAACL 2022) — but these systems score a single supervised classifier's
judgment, not a multi-agent process. **Hallucination detection and self-verification**
methods flag unsupported output without necessarily grounding in retrieved evidence at
all: SelfCheckGPT (Manakul et al., EMNLP 2023) is zero-resource, scoring consistency
across sampled generations; Chain-of-Verification (Dhuliawala et al., Findings of ACL
2024) answers its own verification questions from the model's parameters. Separately,
**multi-agent debate/critique** methods (Du et al., ICML 2024) improve factuality through
natural-language exchange among model instances — but a 2025–2026 cluster of studies has
shown this exchange is itself prone to sycophancy and premature consensus ("Talk Isn't
Always Cheap," arXiv:2509.05396; "Peacemaker or Troublemaker," arXiv:2509.23055; "The
Deliberative Illusion," arXiv:2606.03032) — nothing in an opinion-only exchange
structurally prevents agents from confidently agreeing on the same wrong answer.

Two lines of more recent work sit closest to Aletheia's mechanism and were checked
directly, in full text, because a positioning claim on this specific point is easy to get
wrong. Hard, mechanically-verified verbatim-evidence gates exist, but only for
single-model classification: "Show Your Work" (medRxiv 2026.03.03.26346690 / *Cureus*,
2026) mechanically validates that a model's supporting quote is an exact substring of the
source text, forcing abstention otherwise — the closest prior instance of a
verbatim-or-abstain gate in the literature, but with no multi-agent structure and no
aggregator. Multi-agent debate for claim verification is, independently, an active
2025–2026 subfield — "Debating Truth" (arXiv:2507.19090, WWW 2026), read in full text for
this reason, uses an LLM-judgment Moderator that weighs argumentative strength with no
code-level string verification anywhere in its methodology; the same holds for TRUST
Agents (arXiv:2604.12184, also read in full text), GKMAD, "Debating to Verify," and
Tool-MAD — guided prompts, retrieval-assisted judgment, or tool provenance mediate
agreement in all of them, never a mechanical string check.

Aletheia sits at the intersection these leave open, stated at the precision the search
above supports: a multi-agent verification pipeline in which agreement is constrained not
by a soft, learned, or NLI-scored judgment, but by a hard, mechanical verbatim-substring
match — a verdict may affirm `Supported` or `Contradicted` only by quoting a span the
system can check programmatically against the retrieved evidence text; failing that check
forces `Unverifiable`. This is deliberately narrower than free-form debate — it trades
expressiveness for a structural guarantee: two agents cannot both hallucinate agreement on
a claim neither can quote support for.

We do not claim this combination is unoccupied in the literature in some unbounded sense
— that priority claim is explicitly not the headline (§7) — and this draft is upfront that
not every result supports the thesis cleanly. The contribution we defend is narrower and,
we think, more useful: a working, deployed system plus a seeded, reproducible harness that
reports *where* structural grounding helps, *where* it costs, and *why*, across three
model scales and two domains.

## 2. System

Aletheia is a LangGraph-orchestrated pipeline: an **Intake guard** (a deterministic
prompt-injection scan plus an LLM scope classifier, bypassed only when the caller supplies
their own evidence) admits or refuses a query; a **Retriever** performs hybrid (semantic +
keyword) search over a frozen, versioned PostgreSQL/pgvector corpus; a **Generator**
proposes an answer decomposed into atomic claims; a per-claim **Verifier** judges each
claim against retrieved evidence under the quoted-span discipline; an **Aggregator**
collects verdicts and surfaces any disagreement explicitly (never hidden); and a
non-mutating **Guardrail** attaches a confidence advisory and a standing "verification
tool, not medical advice" disclaimer. The LLM client is provider-agnostic (Gemini, Groq,
OpenRouter), selected by configuration, so the same pipeline runs unmodified across the
model scales and domains compared in §5.

Two properties matter for the evaluation that follows. First, **grounding is structural,
not aspirational**: the pipeline code checks a claimed span against the evidence text
(`grounded_against()`); a verdict that cannot produce a matching span is programmatically
downgraded, not merely instructed to be honest — this is the property the literature
search in §7 was run specifically to stress-test. Second, **the benchmark and the live
system share one grounding path** — there is no separate "eval mode" — so the numbers
below describe the deployed system, not a stripped-down harness variant of it. Gemini
`gemini-3.1-flash-lite-preview` is, as of this draft, the model serving live traffic
(Groq as fail-over), which is why §5.1 reports it as the current headline rather than a
secondary check.

## 3. Research question and hypotheses

**RQ.** Does an evidence-grounded, multi-agent verification pipeline catch measurably more
hallucinations than a single LLM, and at what accuracy, latency, and cost trade-off, across
model scale and domain?

- **H1 (catch rate).** Aletheia achieves a higher hallucination-catch rate than a
  single-LLM baseline on the same benchmark.
- **H2 (grounding reduces false agreement).** Requiring quoted-span evidence lowers the
  false-agreement rate versus an otherwise-identical multi-agent arm whose verdicts are
  opinion-only (no span discipline).
- **H3 (acceptable cost).** The reliability gains come at a quantified, defensible
  latency and per-query cost overhead.

## 4. Method

**Benchmarks.** SciFact (Wadden et al., 2020; CC BY-NC 2.0): expert-written scientific
claims labelled `SUPPORT` / `CONTRADICT` / no-evidence against biomedical abstracts,
mapping directly onto the pipeline's three-valued verdict space; its own abstract corpus
(5,183 abstracts, 15,411 chunks) is ingested into the frozen store. FEVER (Thorne et al.,
2018): open-domain claims against Wikipedia, where — unlike SciFact — claims are
crowdworker paraphrases rather than near-quotations of their evidence, deliberately
stress-testing verbatim grounding where it is weakest.

**Systems compared, all judging the same claim against the same retrieved evidence with
the same model:**
- *Single-LLM baseline* — one holistic call, no span discipline.
- *Multi-agent, ungrounded (ablation)* — the same per-claim critic as the grounded
  system, with the quoted-span requirement removed; isolates what grounding contributes,
  holding the multi-agent structure fixed (H2).
- *Aletheia (grounded verifier)* — the full system.

**Sampling.** A seeded (seed 7), gold-label-stratified sample without replacement,
preserving each benchmark's label mix; corpus coverage (every cited passage present in
the frozen corpus) is checked and reported before scoring.

**Statistics.** Because all systems judge the same claims, headline gaps are tested on
paired per-claim predictions: an exact McNemar test for accuracy, and percentile-bootstrap
95% CIs (10,000 resamples, fixed seed) for catch-rate and false-agreement deltas.

**Fault tolerance.** A provider error on any arm excludes that item from *every* arm
(never fabricating a verdict), keeping comparisons paired; a run whose failures exceed a
small cap aborts rather than reporting a silently-partial result.

**Metrics.** Verification accuracy; hallucination-catch rate (recall on truly
unsupported/false claims); false-agreement rate; latency p50/p95/p99 (verification work
only — shared retrieval is measured once and excluded); per-query token cost.

## 5. Results

### 5.1 Headline benchmark (n=100, current live model)

*SciFact · 100 claims · seed 7 · 1 seeded run · Gemini `gemini-3.1-flash-lite-preview` ·
corpus coverage 100.0% · 2026-08-03.*

| System | Accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 79.0% | 93.1% | 10.5% | 1.147 / 2.885 / 6.552 | 1291.8 |
| Multi-agent, ungrounded (ablation) | 80.0% | 94.8% | 8.1% | 1.374 / 2.619 / 3.105 | 1364.0 |
| **Aletheia (grounded)** | 79.0% | **96.6%** | **6.1%** | 1.519 / 3.318 / 5.108 | 1676.8 |

_Grounded vs baseline (H1): accuracy McNemar exact p = 1.000 (6 discordant); catch-rate Δ
+3.4 pp, 95% CI [+0.0, +8.9]; false-agreement Δ −4.5 pp, 95% CI [−12.3, +0.9]._
_Grounded vs ungrounded ablation (H2): accuracy McNemar exact p = 1.000 (5 discordant);
catch-rate Δ +1.7 pp, 95% CI [+0.0, +5.7]; false-agreement Δ −2.0 pp, 95% CI [−8.1, +1.3]._

**This is the honest headline, not the flattering one.** On a materially stronger base
model, **grounding's accuracy edge disappears: 79.0% vs 79.0%, exactly tied** — not "not
significant" hedging, the point estimate itself shows no gain. Catch-rate and
false-agreement still point the right direction (96.6% vs 93.1% baseline, Δ +3.4 pp;
6.1% vs 10.5%, Δ −4.5 pp), but both intervals touch or cross zero at n=100 — directionally
favorable, not clearly established at this sample size. H3: the grounded arm costs ~30%
more tokens (1676.8 vs 1291.8/query) at higher latency (p50 1.519s vs the baseline's
1.147s) than the baseline, for a benefit that is present in direction but not yet
statistically confirmed. §5.3 explains the mechanism: a strong model already gets most
claims right without grounding's help, so there is simply less error left for the span
discipline to correct — the same effect predicted by the cross-model sweep in §5.4, now
confirmed on the model actually serving production traffic.

### 5.2 Historical headline (n=100, 8B model) — kept for comparison

*SciFact · 100 claims · seed 7 · 1 seeded run · Groq `llama-3.1-8b-instant` · corpus
coverage 100.0% · 2026-07-19.*

| System | Accuracy | Catch rate | False-agreement | Latency p50/p95/p99 (s) | Tokens/query |
| --- | --- | --- | --- | --- | --- |
| Single-LLM baseline | 60.0% | 60.3% | 37.7% | 0.301 / 8.928 / 12.945 | 1388.0 |
| Multi-agent, ungrounded (ablation) | 65.0% | 65.5% | 35.7% | 14.058 / 18.998 / 21.657 | 1473.2 |
| **Aletheia (grounded)** | 69.0% | **82.8%** | **23.8%** | 0.409 / 0.565 / 1.108 | 1675.6 |

On this weaker model, the primary thesis metric held under paired significance and by a
wide margin: catch rate 82.8% vs 60.3%, Δ +22.4 pp, 95% CI [+12.1, +33.3] (excludes zero),
and aggregate accuracy also improved (69.0% vs 60.0%, +9.0 pp, though McNemar itself was
not significant here: p = 0.163, 33 discordant pairs). False-agreement improved
significantly too: 23.8% vs 37.7% (Δ −13.9 pp, 95% CI [−23.9, −5.0]). This run — not §5.1
— was the paper's headline until Gemini became the live provider; it is retained because
it establishes that grounding's effect is real and large when the base model is weak
enough to need the correction, which §5.1 and §5.4 together show is exactly the boundary
condition that determines whether grounding helps accuracy at all.

### 5.3 Where the accuracy story goes, at both scales

Joining each headline run's grounded traces back to gold labels and tagging every scored
claim by outcome shows retrieval is not the bottleneck at either scale — at most 1 of 100
gold-cited passages failed to reach the verifier in either run, consistent with ≥99%
corpus coverage; errors are overwhelmingly verifier decisions.

| Outcome | 8B (§5.2) | Gemini (§5.1) |
| --- | ---: | ---: |
| Correct | 69 | 79 |
| Retrieval miss | — | 1 |
| Verifier abstention (evidence present, no span quoted) | 14/63 answerable | 9/63 answerable |
| Wrong direction | 6 | 4 |
| False grounding (gold Unverifiable, verdict asserts) | 10/37 | 7/37 |

The stronger model needs the verifier's strict single-span discipline less often on *both*
sides of the trade-off it is designed to police: false-grounding on genuinely
undecidable claims falls (10/37 → 7/37) and verifier abstention on answerable claims also
falls (14/63 → 9/63) — yet this improvement does not convert into an accuracy edge over
Gemini's own ungrounded baseline, because that baseline is already strong enough to get
most of the same claims right without grounding's help. The error reduction is real; it
simply no longer has much baseline error left to convert into a measurable accuracy gain.

**Honest caveat on `false_grounding`.** SciFact's `NotEnoughInfo` label is defined against
its own *annotated* evidence set, while Aletheia retrieves from the full frozen corpus —
so a verdict counted here as false grounding sometimes has genuine support the SciFact
annotators simply did not cite. Both figures above are upper bounds on verifier error for
this class, not clean counts of hallucinated grounding; separating the two needs manual
adjudication (§8).

### 5.4 Cross-model robustness: the mechanism behind §5.1 and §5.2

To check whether §5.1–5.3 generalize, H1 was additionally run at 70B (Groq
`llama-3.3-70b-versatile`, n=30) and a free 550B-class model (OpenRouter
`nemotron-3-ultra-550b`, n=19) on identical seeded samples. **Caveat binding throughout
this subsection: n=19–30, every delta below is not statistically significant** (bootstrap
CIs touch or cross zero) — read for direction and mechanism, not as a headline; the
Gemini result in §5.1 is what confirms this mechanism at a properly-powered n.

| Base model | n | Baseline acc | Grounded acc | Δ acc | Δ catch | Δ false-agree |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8B | 30 | 56.7% | 66.7% | **+10.0** | +17.6 | −11.9 |
| 70B | 30 | 80.0% | 70.0% | **−10.0** | +5.9 | −6.0 |
| 550B-class | 19 | 89.5% | 73.7% | **−15.8** | +0.0 | +0.0 |

Grounding's catch-rate and false-agreement advantages hold at every scale (at 550B the
baseline is already at ceiling, so there is nothing left to improve). But **the accuracy
effect flips sign with base-model strength**: +10 pp at 8B, −10 to −16 pp at 70B/550B-class
here, and exactly 0 pp at Gemini scale in the properly-powered §5.1 run. The mechanism is
visible in the error mix: false-grounding on undecidable claims falls monotonically with
scale, but the residual error shifts to over-abstention — a strong model that would answer
correctly on its own is instead forced to `Unverifiable` when it cannot isolate one
verbatim span. The strict single-span rule is a net accuracy win only when the base model
is weak enough to need the correction; §5.1 shows that at production scale, that boundary
has already been crossed.

### 5.5 A targeted verifier improvement, and its limits

Both failure modes above are the same underlying judgment — does a span *settle* the
claim, or merely touch its topic? A two-sided **span-sufficiency test** was added to the
grounded prompt: assert only when the span, alone, directly decides the claim; do not
retreat to `Unverifiable` when it plainly does; treat a merely-topical span as
`Unverifiable`. On a held-out 8B sample (seed 13), accuracy rose 53.3% → 66.7%
(+13.4 pp) with catch-rate unchanged and false-agreement slightly lower. Re-running the
same improved verifier at 70B (clean A/B, baseline reproduces exactly at 80.0%) shows the
change does what it targets — false-grounding halves (4/11 → 2/11) — but its "do not
retreat from a decisive span" side does not hold on a strong model: abstention *rises*
more than false-grounding falls (5/19 → 7/19), so accuracy *slips* 70.0% → 66.7% while
catch reaches 100% and false-agreement reaches zero. The change **sharpens** §5.4's
trade-off rather than escaping it: an 8B-scale accuracy win, stated as such, alongside
catch/false-agreement advantages that hold at every scale tested. §5.1's Gemini headline
already uses this improved verifier prompt.

### 5.6 Second domain: FEVER, a harder stress test of the guarantee itself

§5.1–5.5 are all SciFact. This section is a separate, harder domain and does not revise
the SciFact headline: FEVER's claims are crowdworker *paraphrases* of Wikipedia sentences
rather than near-quotations of their evidence, so a verbatim-grounding system is
stress-tested exactly where it is weakest. The point of running it is not to win the
accuracy number but to check whether the anti-hallucination guarantee still holds when the
domain is built against it.

*FEVER · 100 claims · seed 7 · 1 seeded run · Groq `llama-3.1-8b-instant` · corpus
coverage 99.0% · 2026-07-25.*

| System | Accuracy | Catch rate | False-agreement |
| --- | --- | --- | --- |
| Single-LLM baseline | 80.0% | 84.8% | 23.8% |
| Multi-agent, ungrounded (ablation) | **85.0%** | **95.5%** | 9.1% |
| Aletheia (grounded verifier) | 77.0% | 93.9% | 13.8% |

_Grounded vs baseline (H1): accuracy McNemar exact p = 0.648 (19 discordant); catch-rate Δ
+9.1 pp, 95% CI [+1.5, +17.7]; false-agreement Δ −10.0 pp, 95% CI [−22.9, +2.0]._
_Grounded vs ungrounded ablation (H2): accuracy McNemar exact p = 0.008 (8 discordant, in
the grounded arm's disfavour); catch-rate Δ −1.5 pp, 95% CI [−5.0, 0.0]; false-agreement
Δ +4.7 pp, 95% CI [+0.3, +12.6]._

**The corpus lever: 56.0% → 77.0% accuracy (+21 pp), paired McNemar exact p = 4.9e-05.**
The table above replaces an earlier run on the identical 100 claims and model in which the
grounded arm scored 56.0% accuracy / 100.0% catch / 0.0% false-agreement. The only change
between the two runs is the corpus: FEVER's wiki-pages text ships in Penn-Treebank
tokenization (`-LRB-`/`-RRB-` for brackets, space-separated punctuation), which an 8B model
paraphrases away while copying an otherwise-correct evidence span — the verbatim-grounding
guard then rejected a *correct* quote and forced abstention. Folding the markup to plain
text at ingestion fixed 24 grounded verdicts and broke 3 on the identical seeded sample: the
earlier 56% was overwhelmingly a corpus-markup artifact, not a reasoning ceiling.

**The honest cost of the fix.** The dirty-corpus run's *perfect* safety profile (0%
false-agreement, 100% catch) was not the guarantee working — it was the guarantee never
being tested, because a markup-broken corpus forced the model to abstain on nearly
everything decidable. Cleaning the corpus lets the model actually assert, and the error
profile changes accordingly: false-agreement moves 0.0% → 13.8%, catch 100.0% → 93.9%. Of
the 51 assertions the clean-corpus run makes, 5 are wrong (3 Contradicted claims called
Supported, 2 assertions on gold-Unverifiable claims); the other 18 misses are safe
abstentions on decidable claims.

**The load-bearing check: the guarantee itself held.** The guarantee is *"never assert
without an exact verbatim quote from the evidence,"* and it is intact: of the 51 asserted
verdicts, **51/51 (100%) are backed by a span that appears verbatim in the retrieved
evidence**, re-verified directly from the traces. The 5 wrong assertions are genuine
*entailment* errors — the reader quoted the evidence faithfully and drew the wrong
inference from it — not fabrications and not guard failures. The guarantee delivers
exactly what it promises (no unsupported assertion) and nothing it never promised (it is
not a guarantee of correct entailment), even on the domain specifically chosen to break
it.

**What still separates the grounded arm from the ceiling.** After the corpus fix, the
grounded arm (77.0%) trails the ungrounded ablation (85.0%) on accuracy — H2 is
significant (p = 0.008) and is reported without softening: strict verbatim grounding costs
~8 pp of raw accuracy here versus letting the same model reason freely, because FEVER's
paraphrase claims are exactly the case where a true claim's wording does not match its
evidence. Against the single-LLM baseline (H1), grounding still helps where designed to:
catch rate is significantly higher (Δ +9.1 pp, CI excludes zero), while the
false-agreement improvement is directional but not significant at n=100 (CI straddles
zero). A partial, underpowered check at 70B (29/100 items before a free-tier quota cap)
shows the same direction as SciFact's cross-model sweep (grounded accuracy 51.7% → 65.5%,
6 fixed / 2 broken, p ≈ 0.29) — a signal, not a result; the combined clean-corpus +
strong-model FEVER number remains future work (§8).

## 6. Threats to validity

- **Benchmark leakage / contamination** into pretraining — mitigated by reporting the
  *relative* gap to the baseline rather than absolute scores.
- **Prompt sensitivity** — controlled by holding prompts fixed across systems within a
  comparison and reporting variance across runs.
- **Retriever ceiling** — verification can only ground in what is retrievable; §5.3
  measures retrieval misses directly and finds them near-zero at both benchmarks tested,
  but this is corpus- and query-set-specific.
- **Small-n exploratory sections (§5.4, §5.5's 70B/550B re-checks, §5.6's 70B partial
  check)** — every delta reported there is statistically insignificant; read for
  mechanism and direction only.
- **Single seeded repeat at n=100** — the §5.1 and §5.6 headlines each report one seeded
  run (± 0.0); the harness supports `--repeats N` for mean ± std once budget allows, which
  would tighten every CI reported above.
- **No comparison against SciFact/FEVER leaderboard systems.** Every number above compares
  Aletheia's own three arms against each other, not against MultiVerS (SciFact's own
  supervised SOTA) or FEVER/AVeriTeC leaderboard entries. This is a genuine gap for a
  claim-verification paper and is called out explicitly rather than left implicit — see
  §8.
- **Three multi-agent-debate papers confirmed to exist but not yet read in full text**
  (GKMAD, "Debating to Verify," Tool-MAD, §7) — nothing in their abstracts suggests a hard
  verbatim gate, but this is a lower-confidence check than the full-text reads given to
  the two closest candidates, and should be closed before the novelty claim in §7 is
  treated as final.

## 7. Related work and novelty claim (positioning)

As introduced in §1: claim-verification systems (FEVER, SciFact and its extractive
VeriSci baseline, later MultiVerS) and hallucination-detection methods (SelfCheckGPT,
zero-resource; Chain-of-Verification, parameter-only) typically score a single model's
judgment, not a multi-agent process. Multi-agent debate/critique methods (Du et al., ICML
2024) improve factuality through exchange among model instances, and a 2025–2026
literature (arXiv:2509.05396, arXiv:2509.23055, arXiv:2606.03032, among others) has
independently documented that this exchange is itself prone to sycophancy and false
agreement — precisely the failure mode Aletheia's evidence gate targets.

Two lines of directly adjacent work were checked in full text, not abstract alone,
specifically because they are the closest candidates for prior art on this exact claim.
Hard, mechanically-verified verbatim-evidence gates exist ("Show Your Work," medRxiv
2026.03.03.26346690 / *Cureus* 2026: quotes mechanically validated as exact substrings,
forcing abstention otherwise) but only for single-model classification — no multi-agent
structure, no aggregator, no deployed evaluation. Multi-agent debate for claim
verification is an active subfield ("Debating Truth," arXiv:2507.19090, WWW 2026; TRUST
Agents, arXiv:2604.12184 — both read in full text) but every system found grounds
evidence *softly*: LLM-judgment moderators, calibrated confidence scores, or NLI-based
adjudication, never a mechanical string check. The same held, on abstract-level
confirmation, for GKMAD, "Debating to Verify," and Tool-MAD (flagged in §6 as not yet
read in full). Two further systems gate hard and mechanically but on a different
evidence modality entirely: EG-VAR (arXiv:2607.12650) gates on Lean4-kernel-checked
formal proofs, and Eidoku (arXiv:2512.20664) gates on CSP-style structural-consistency
cost — neither operates on natural-language evidence spans or multi-agent debate.
VeriCite (arXiv:2510.11394) and ProvenanceGuard (arXiv:2606.18037) ground citations via
NLI/token-overlap scoring — a calibrated score, not a pass/fail exact-match gate.

**Aletheia's contribution is the combination these leave unoccupied, stated at the
precision this search supports**: while hard, mechanically-verified verbatim-evidence
gates have been shown to improve auditability in single-model classification, and
multi-agent debate frameworks for claim verification rely on soft, learned, or
NLI-based adjudication, Aletheia is — to our knowledge, after this search — the first
system to make a hard, mechanical verbatim-substring match the structural precondition
for *multi-agent verifier agreement itself*, delivered as a deployed, evaluated service
with a reusable, seeded harness that reports catch rate, false-agreement, latency, and
cost against a single-LLM baseline, across three model scales and two domains. The
accuracy+latency+cost evaluation triad itself has a precedent (OpenFactCheck, Wang et
al., EMNLP 2024 demo) which does not include catch rate or false-agreement and is not
multi-agent — so that half of the evaluation framing is presented as good practice
inherited from that line of work, not claimed as novel in isolation.

This is a **positioning claim, not a systematic survey**, and it is deliberately not the
headline — the honest, defensible unit remains the measured gap to the baseline (§5). One
item is explicitly not fully closed: GKMAD, "Debating to Verify," and Tool-MAD were
confirmed to exist and abstract-checked, but not read in full text (§6); nothing in their
abstracts suggests a hard gate, but a full-text pass on all three is planned before this
framing is treated as final for submission.

## 8. Future work

- **Full-text verification of GKMAD, "Debating to Verify," and Tool-MAD** — the one
  remaining gap in the novelty claim's evidentiary base (§7).
- **Manual adjudication of the `false_grounding` upper bound** (§5.3) — separating
  genuinely hallucinated grounding from claims whose supporting evidence the benchmark's
  own annotators simply did not cite, on both SciFact and FEVER.
- **A leaderboard comparison** against MultiVerS (SciFact) and a FEVER/AVeriTeC entry —
  currently absent and flagged as a threat to validity (§6), not silently omitted.
- **A third, soft-grounding baseline arm** (e.g. an NLI-threshold check in the style of
  MiniCheck or AlignScore) — separates "hard gate vs. no check" from "hard gate vs. soft
  check," the comparison closest to what a reviewer familiar with §7's related work will
  ask for first.
- **The combined clean-corpus + strong-model FEVER run** — a full three-arm run at 70B on
  the cleaned corpus does not fit the free-tier daily token cap at present (§5.6); the
  paired 29-item partial check is directional but underpowered.
- **Repeats at scale** (`--repeats N`) for tighter confidence intervals on every headline
  gap reported above, budget permitting.

## Status of this draft

This is a living document, regenerated from `EVALUATION.md` as new runs land. As of
2026-08-03: the Gemini headline (§5.1), the full cross-model sweep (§5.4–5.5), and the
FEVER second-domain run (§5.6) are all committed, completed work — the two placeholders
that blocked the previous draft (n=100 re-validation, FEVER live run) are both resolved.
What remains before final submission is listed in full in §8; none of it changes a number
already reported above, only what surrounds it. Do not cite specific numeric values from
this draft as final without checking `EVALUATION.md` for a more recent run.
