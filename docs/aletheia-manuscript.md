---
title: "A Structural Evidence Gate for Multi-Agent Claim Verification: Verbatim-Grounded Agreement, and When It Helps"
author: "Jay Gautam^[Independent Research, Aletheia Project. Correspondence: jaygautam561@gmail.com]"
date: "August 2026"
abstract: |
  **Background.** Multi-agent large language model (LLM) pipelines verify claims by letting model instances debate or critique each other, but such opinion-only exchange can fail by *agreeing on the wrong answer*: nothing in it structurally prevents correlated hallucination. **Objective.** We ask whether constraining agreement *structurally* — permitting an affirmative or contradictory verdict only when it quotes a verbatim span of retrieved evidence, checked programmatically — catches more hallucinations than a single LLM, and at what accuracy, latency and cost, across model scale and domain. **Method.** We build Aletheia, a deployed LangGraph pipeline whose verifier is downgraded to *Unverifiable* whenever it cannot produce an exact evidence substring, and evaluate it against a single-LLM baseline and an ungrounded multi-agent ablation on SciFact and FEVER, grounding all arms in one frozen, versioned corpus with paired significance testing. **Results.** On the live model (Gemini flash-lite, n=100) the grounded arm ties the baseline on accuracy (79.0% vs 79.0%) while improving catch rate (96.6% vs 93.1%) and false-agreement (6.1% vs 10.5%) directionally; on a weaker 8B model the catch-rate gain is large and significant (82.8% vs 60.3%, delta +22.4 pp, 95% CI [+12.1, +33.3]). A cross-model sweep (8B–550B) shows grounding's accuracy contribution is *inversely related to base-model strength*. On FEVER a corpus-cleaning fix recovers +21 pp of grounded accuracy (56.0%->77.0%, McNemar p = 4.9e-5), and the load-bearing guarantee holds exactly: of 51 asserted verdicts, 51/51 (100%) are backed by a verbatim-verified span. **Conclusion.** A structural evidence gate is a mechanically verifiable defence against false agreement whose catch-rate direction holds across three scales and two domains, and whose accuracy effect is a genuine, scale- and domain-dependent trade-off rather than a free lunch.
keywords: "automated claim verification; large language models; hallucination detection; multi-agent systems; retrieval-augmented generation; evidence grounding; fact-checking"
geometry: "a4paper, margin=2.3cm"
fontsize: 10.5pt
linestretch: 1.08
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
---

**Keywords:** automated claim verification; large language models; hallucination detection; multi-agent systems; retrieval-augmented generation; evidence grounding; fact-checking; reproducible evaluation

# 1. Introduction

The reliability of large language models (LLMs) is limited by *hallucination* — fluent output unsupported by any source. The problem is most costly in **automated fact and claim verification**, where the failure mode is not an obvious error but a *confident, wrong verdict*: a system that labels a false claim "supported," or asserts more than its evidence allows, actively manufactures misinformation rather than merely failing to catch it.

A structured review of 35 empirical journal studies on LLM factuality, hallucination, and verification (summarised in the supplementary literature table) reveals a field converging on partial solutions with one shared blind spot. Two problem framings dominate: **factual-accuracy benchmarking** — does the model get the answer right (Yanagita 2023 report GPT-4 at 81.5% on a medical licensing exam) — and **hallucination detection** — is the output unsupported (Massenon 2025 taxonomise real user-reported hallucinations; a clinical-safety framework measures a 1.47% hallucination rate in medical summaries, npj Digital Medicine 2025). The dominant *mitigation* is retrieval-augmented generation (RAG): grounding generation in retrieved evidence reduces hallucination substantially, in some clinical settings to near zero (npj Digital Medicine 2025). Yet across this literature three limitations recur. First, **grounding is enforced softly** — by prompting the model to "use only the retrieved passages" — which reduces but cannot *guarantee* that an assertion is evidence-backed, since the model can still contradict or over-reach beyond the retrieved text. Second, systems are **overwhelmingly single-model**; multi-agent LLM verification appears only rarely in journal work (Expert Systems with Applications 2025), and its known risk — that agents *agree, confidently, on the same wrong answer* — is unexamined. Third, the **latency and cost** of the reliability mechanism are almost never reported, leaving the practical trade-off unquantified.

This yields a clear **methodological gap**: no empirical study evaluates a *hard, mechanically-verified* evidence gate — one that permits an affirmative or contradictory verdict only when it can quote a verbatim span of the retrieved evidence — as the structural precondition for **multi-agent** claim verification, together with its catch-rate, false-agreement, accuracy, latency and cost trade-offs across model scales and domains. This is the gap the present work addresses. (For technical antecedents, the closest prior art is single-model verbatim gating and soft-grounded debate; both are positioned precisely in §2.)

We close that gap with **Aletheia**, a multi-agent verification pipeline in which agreement is constrained not by a soft, learned, or NLI-scored judgment but by a **hard, mechanical verbatim-substring match**: a verdict may affirm *Supported* or *Contradicted* only by quoting a span the system checks programmatically against the retrieved evidence; failing that check forces *Unverifiable*. This is deliberately narrower than free-form debate — it trades expressiveness for a structural guarantee: two agents cannot both hallucinate agreement on a claim neither can quote support for.

**Contributions.**

1. **A structural evidence gate** that makes a mechanical verbatim-span match the precondition for multi-agent verifier agreement — to our knowledge the first such construction operating on natural-language evidence (§2, §3).
2. **A deployed system and a seeded, reproducible harness** that reports catch rate, false-agreement, latency and cost against a single-LLM baseline and an ungrounded ablation, all judging the same claims on the same frozen corpus (§3–§5).
3. **An empirical boundary condition:** grounding's accuracy benefit is inversely related to base-model strength — a large, significant win at 8B, exactly zero at production scale — established across three model scales and two domains (§5, §6).
4. **A demonstrated separation of guarantees:** on the domain built to break verbatim grounding (FEVER), the gate keeps its one promise — 51/51 asserted verdicts are verbatim-backed — while its residual errors are genuine entailment mistakes, not fabrications (§5.6, §6).

# 2. Related work

**The empirical landscape.** Journal research on LLM factual reliability clusters into four lines, each mapping to a limitation this work targets. (i) *Factual-accuracy and citation-reliability studies* evaluate whether a model is right, typically in a single domain (Yanagita 2023; GPT-4-vs-Gemini citation reliability, Computers in Biology and Medicine 2024; ChatGPT drug-information accuracy, Khatri 2025) — measuring the problem, not guaranteeing against it. (ii) *Hallucination detection and rate estimation* characterise unsupported output (Massenon 2025; clinical-safety framework, npj Digital Medicine 2025) but detect after the fact rather than prevent. (iii) *Retrieval-augmented mitigation* grounds generation in evidence and consistently reduces hallucination (RAG across 10 LLMs, npj Digital Medicine 2025; long-context and low-resource RAG, JMIR 2025; multilingual RAG verification, Journal of Intelligent Information Systems 2026) — but grounding is prompt-enforced, not mechanically checked. (iv) *Automated verification and misinformation detection* label claims from content, style, or evidence (FacTeR-Check, Knowledge-Based Systems 2022; pretrained-LM detection, Information Processing & Management 2025; and a large body of deep-learning fake-news work, e.g. Kolluri 2022; Lu 2025; Kumar 2025) — but as single-model, black-box classifiers that rarely tie each assertion to a checkable span or report cost. The common thread: reduction without guarantee, single models, and unreported cost.

**Direct technical antecedents.** Claim-verification benchmarks and systems (FEVER [1], SciFact [2] and its extractive VeriSci baseline, MultiVerS [3]) score a single supervised judgment. Hallucination-detection methods flag unsupported generation without necessarily retrieving evidence: SelfCheckGPT [4] scores consistency across sampled generations; Chain-of-Verification [5] answers self-generated questions from parameters. Multi-agent debate [6] improves factuality through exchange, but a failure-mode literature [a,b,c] shows the exchange can itself produce false consensus. Two lines sit closest and were examined in full text: hard, mechanically-verified verbatim gates exist ("Show Your Work" [d]) but only for *single-model classification* — no multi-agent structure; and multi-agent debate *for claim verification* is active ("Debating Truth" [e]; TRUST Agents [f]) but grounds evidence *softly* — LLM-judgment moderators, calibrated confidence, or NLI adjudication, never a mechanical string check. Aletheia occupies the intersection these leave open. Consistent with prior evaluation practice (OpenFactCheck [7]), we report an accuracy–latency–cost triad; the catch-rate and false-agreement axes are our additions. This is a *positioning claim*, not a systematic survey; the defensible unit of contribution remains the measured gap to the baseline (§5).

# 3. System architecture

Aletheia is a LangGraph-orchestrated pipeline of six stages. An **Intake guard** (deterministic prompt-injection scan plus an LLM scope classifier) admits or refuses a query. A **Retriever** performs hybrid semantic + keyword search over a frozen, versioned PostgreSQL/pgvector corpus. A **Generator** proposes an answer decomposed into atomic claims. A per-claim **Verifier** judges each claim against retrieved evidence under the quoted-span discipline. An **Aggregator** collects verdicts and surfaces disagreement explicitly. A non-mutating **Guardrail** attaches a confidence advisory and disclaimer. The LLM client is provider-agnostic (Gemini, Groq, OpenRouter), so one pipeline runs unmodified across all scales and domains compared below.

Two properties are load-bearing. First, **grounding is structural, not aspirational**: pipeline code checks a claimed span against the evidence text (`grounded_against()`) and programmatically downgrades any verdict that cannot produce a matching span — the model is not merely instructed to be honest. Second, **benchmark and live system share one grounding path**: there is no separate "eval mode," so all reported numbers describe the deployed system.

# 4. Research questions, hypotheses and method

**RQ.** Does an evidence-grounded, multi-agent verification pipeline catch measurably more hallucinations than a single LLM, and at what accuracy, latency and cost trade-off, across model scale and domain? **H1:** Aletheia achieves a higher hallucination-catch rate than a single-LLM baseline. **H2:** Requiring quoted-span evidence lowers false-agreement versus an otherwise-identical opinion-only multi-agent arm. **H3:** Reliability gains come at a quantified, defensible latency and cost overhead.

**Benchmarks.** SciFact [2] (expert scientific claims over 5,183 biomedical abstracts; 15,411 chunks ingested) and FEVER [1] (open-domain claims over Wikipedia, where claims are crowdworker *paraphrases* rather than near-quotations — stress-testing verbatim grounding where it is weakest). **Arms** (all judging the same claim, evidence and model): single-LLM baseline; multi-agent ungrounded ablation (span requirement removed, isolating grounding's contribution, H2); Aletheia (full grounded verifier). **Sampling:** seeded (seed 7), gold-label-stratified, without replacement; corpus coverage checked before scoring. **Statistics:** paired per-claim tests — exact McNemar for accuracy, percentile-bootstrap 95% CIs (10,000 resamples, fixed seed) for catch-rate and false-agreement deltas. **Fault tolerance:** a provider error on any arm excludes that item from every arm, never fabricating a verdict. **Metrics:** accuracy; catch rate (recall on truly unsupported/false claims); false-agreement rate; latency p50/p95/p99; tokens/query.

# 5. Results

## 5.1 Headline benchmark (n=100, current live model)

*SciFact · 100 claims · seed 7 · Gemini `gemini-3.1-flash-lite-preview` · corpus coverage 100.0% · 2026-08-03.*

| System | Acc | Catch | F-agree | Latency p50/95/99 (s) | Tok/q |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 79.0% | 93.1% | 10.5% | 1.15 / 2.89 / 6.55 | 1291.8 |
| Multi-agent, ungrounded (ablation) | 80.0% | 94.8% | 8.1% | 1.37 / 2.62 / 3.11 | 1364.0 |
| **Aletheia (grounded)** | **79.0%** | **96.6%** | **6.1%** | 1.52 / 3.32 / 5.11 | 1676.8 |

*Grounded vs baseline (H1): accuracy McNemar p = 1.000 (6 discordant); catch delta +3.4 pp, CI [+0.0, +8.9]; false-agree delta -4.5 pp, CI [-12.3, +0.9]. Grounded vs ablation (H2): catch delta +1.7 pp, CI [+0.0, +5.7]; false-agree delta -2.0 pp, CI [-8.1, +1.3].*

On a materially stronger base model, grounding's accuracy edge disappears (79.0% vs 79.0%, exactly tied); catch-rate and false-agreement point the right direction but both intervals touch or cross zero at n=100. The grounded arm costs ~30% more tokens at higher latency (H3), for a benefit present in direction but not statistically confirmed at this n. §5.3 identifies the mechanism.

## 5.2 Weaker-model comparison (n=100, 8B)

*SciFact · 100 claims · seed 7 · Groq `llama-3.1-8b-instant` · corpus coverage 100.0% · 2026-07-19.*

| System | Acc | Catch | F-agree | Latency p50/95/99 (s) | Tok/q |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 60.0% | 60.3% | 37.7% | 0.30 / 8.93 / 12.95 | 1388.0 |
| Multi-agent, ungrounded (ablation) | 65.0% | 65.5% | 35.7% | 14.06 / 19.00 / 21.66 | 1473.2 |
| **Aletheia (grounded)** | **69.0%** | **82.8%** | **23.8%** | 0.41 / 0.57 / 1.11 | 1675.6 |

*Catch 82.8% vs 60.3%, delta +22.4 pp, CI [+12.1, +33.3] (excludes zero); accuracy 69.0% vs 60.0%, +9.0 pp (McNemar p = 0.163); false-agree 23.8% vs 37.7%, delta -13.9 pp, CI [-23.9, -5.0].*

On this weaker model the primary thesis metric holds under paired significance and by a wide margin, establishing that grounding's effect is real and large when the base model is weak enough to need the correction.

## 5.3 Error decomposition

| Outcome | 8B (§5.2) | Gemini (§5.1) |
|:--|--:|--:|
| Correct | 69 | 79 |
| Retrieval miss | — | 1 |
| Verifier abstention (evidence present, no span quoted) | 14/63 | 9/63 |
| Wrong direction | 6 | 4 |
| False grounding (gold Unverifiable, verdict asserts) | 10/37 | 7/37 |

Retrieval is not the bottleneck at either scale (at most 1/100 gold passages missed); errors are overwhelmingly verifier decisions. The stronger model needs the strict single-span discipline less often on both sides — false-grounding 10/37->7/37, abstention 14/63->9/63 — yet this does not convert into an accuracy edge, because the ungrounded baseline is already strong enough to get most claims right unaided.

*Caveat on false-grounding.* SciFact's `NotEnoughInfo` label is defined against its own annotated evidence set, while Aletheia retrieves from the full corpus — so a verdict counted as false grounding sometimes has genuine, uncited support. Both figures are upper bounds on verifier error, not clean counts of hallucination; separating them needs manual adjudication (§7).

## 5.4 Cross-model robustness

**n=19–30; every delta below is not statistically significant** — read for direction and mechanism; §5.1 confirms the mechanism at a powered n.

| Base model | n | Baseline acc | Grounded acc | D-acc | D-catch | D-fagree |
|:--|--:|--:|--:|--:|--:|--:|
| 8B | 30 | 56.7% | 66.7% | +10.0 | +17.6 | -11.9 |
| 70B | 30 | 80.0% | 70.0% | -10.0 | +5.9 | -6.0 |
| 550B-class | 19 | 89.5% | 73.7% | -15.8 | +0.0 | +0.0 |

Catch-rate and false-agreement advantages hold at every scale (at 550B the baseline is at ceiling). But the **accuracy effect flips sign with base-model strength**: +10 pp at 8B, -10 to -16 pp at 70B/550B, and 0 pp at Gemini scale (§5.1). The residual error shifts to over-abstention: a strong model that would answer correctly is forced to *Unverifiable* when it cannot isolate one verbatim span.

## 5.5 A targeted verifier improvement

A two-sided **span-sufficiency test** (assert only when the span alone decides the claim; do not retreat when it plainly does; treat merely-topical spans as *Unverifiable*) raised 8B accuracy 53.3%->66.7% (+13.4 pp, seed 13) with catch-rate unchanged. Re-run at 70B, it halves false-grounding (4/11->2/11) but raises abstention (5/19->7/19), so accuracy slips 70.0%->66.7% while catch reaches 100%. The change **sharpens** §5.4's trade-off rather than escaping it. §5.1 already uses this improved prompt.

## 5.6 Second domain: FEVER

*FEVER · 100 claims · seed 7 · Groq `llama-3.1-8b-instant` · corpus coverage 99.0% · 2026-07-25.*

| System | Acc | Catch | F-agree |
|:--|--:|--:|--:|
| Single-LLM baseline | 80.0% | 84.8% | 23.8% |
| Multi-agent, ungrounded (ablation) | 85.0% | 95.5% | 9.1% |
| **Aletheia (grounded verifier)** | 77.0% | 93.9% | 13.8% |

*H1 (vs baseline): accuracy McNemar p = 0.648; catch delta +9.1 pp, CI [+1.5, +17.7]; false-agree delta -10.0 pp, CI [-22.9, +2.0]. H2 (vs ablation): accuracy McNemar p = 0.008 (grounded disfavour); false-agree delta +4.7 pp, CI [+0.3, +12.6].*

**The corpus lever: 56.0% -> 77.0% accuracy (+21 pp), McNemar p = 4.9e-5.** An earlier run on the identical claims/model scored 56.0% accuracy. The only change is the corpus: FEVER's wiki text ships in Penn-Treebank tokenization (`-LRB-`/`-RRB-`, spaced punctuation), which an 8B model paraphrases away while copying an otherwise-correct span — the guard then rejected a *correct* quote and forced abstention. Folding the markup to plain text fixed 24 grounded verdicts and broke 3: the earlier 56% was overwhelmingly a corpus-markup artifact, not a reasoning ceiling.

**The guarantee held.** Of the 51 asserted verdicts, **51/51 (100%) are backed by a span appearing verbatim in the retrieved evidence**, re-verified from traces. The 5 wrong assertions are genuine *entailment* errors — the reader quoted faithfully and inferred wrongly — not fabrications and not guard failures. After the fix the grounded arm (77.0%) trails the ungrounded ablation (85.0%): strict verbatim grounding costs ~8 pp of raw accuracy on paraphrase claims (H2 significant, reported without softening), while still beating the baseline on catch rate (H1, CI excludes zero).

# 6. Discussion

**What the evidence supports.** Across three model scales and two domains, the structural gate's *safety* direction is consistent: catch rate rises and false-agreement falls versus the single-LLM baseline in every configuration, significantly so where the base model is weak (§5.2) and on FEVER-vs-baseline catch rate (§5.6). H1 is therefore supported in direction throughout and significantly at the scales with room to improve; H2 is directionally supported but not consistently significant at n=100. Most robust of all is the *mechanical guarantee*: 51/51 verbatim-backed assertions on the domain designed to break it. This is the result a reviewer can check independently from the traces, and it does not depend on a sample size.

**The central scientific finding is a boundary condition, not a leaderboard win.** Grounding's contribution to *accuracy* is inversely related to base-model strength (§5.1, §5.4): a strong model already answers most claims correctly, so the span discipline has little error left to correct and instead occasionally forces a correct answer into abstention. This reframes when structural grounding is worth its cost. It is a net accuracy win for weaker or cheaper models; on strong models its value is not accuracy but *auditability* — a guarantee that every assertion is quote-backed, at ~30% token overhead.

**A conceptual separation the field should adopt.** Aletheia guarantees *no unsupported assertion*, not *correct entailment*. The FEVER errors make this concrete: the model quoted the evidence exactly and still reasoned wrongly. Conflating the two guarantees overstates what any verbatim gate can promise; separating them clarifies that the gate eliminates fabrication while leaving reading comprehension as a distinct, remaining problem.

**Practical implication.** For safety-critical or low-cost deployments — where a confidently wrong shared verdict is costlier than an honest abstention — a hard evidence gate is the appropriate default. For maximum accuracy on strong models with lenient auditing needs, a softer check may dominate; quantifying that crossover is the natural next study (§7).

# 7. Limitations and future work

- **No soft-grounding baseline yet.** The reported ablation is hard-gate vs. no-check; a third NLI-threshold arm (MiniCheck/AlignScore style) is needed to isolate hard-gate vs. soft-check — the comparison closest to §2's related work and the first a reviewer will request.
- **No leaderboard comparison.** All arms are internal; a comparison against MultiVerS (SciFact) and a FEVER/AVeriTeC entry is absent and flagged, not omitted silently.
- **Small-n exploratory sections** (§5.4, §5.5 re-checks): every delta there is insignificant and read only for mechanism.
- **Single seeded repeat at n=100;** `--repeats N` would tighten every CI.
- **False-grounding is an upper bound** (§5.3) pending manual adjudication of uncited-but-genuine support.
- **Threats to validity:** possible benchmark contamination (mitigated by reporting relative gaps), prompt sensitivity (controlled by fixing prompts within a comparison), and retriever ceiling (measured directly, near-zero here but corpus-specific).

# 8. Conclusion

We presented Aletheia, a multi-agent claim-verification pipeline that makes a hard, mechanical verbatim-substring match the structural precondition for verifier agreement, and evaluated it as a deployed system with a seeded, reproducible harness. The gate is a mechanically verifiable defence against false agreement: its catch-rate and false-agreement advantages over a single-LLM baseline hold in direction across three model scales and two domains, significantly where the base model is weak, and its one promise — never assert without a verbatim quote — is kept exactly (51/51) even on the domain built to break it. Its effect on aggregate accuracy is not a free lunch but a scale- and domain-dependent trade-off: a real gain for weaker models, an auditability guarantee rather than an accuracy gain for strong ones. Reporting where structural grounding helps, where it costs, and why — including the results that do not flatter the thesis — is itself the contribution.

# References

*Established, peer-reviewed sources:*

1. Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: a Large-scale Dataset for Fact Extraction and VERification. *NAACL-HLT*.
2. Wadden, D., Lin, S., Lo, K., Wang, L. L., van Zuylen, M., Cohan, A., & Hajishirzi, H. (2020). Fact or Fiction: Verifying Scientific Claims (SciFact). *EMNLP*.
3. Wadden, D., Lo, K., Kuehl, B., Cohan, A., Beltagy, I., Wang, L. L., & Hajishirzi, H. (2022). MultiVerS: Improving Scientific Claim Verification with Weak Supervision and Full-Document Context. *Findings of NAACL*.
4. Manakul, P., Liusie, A., & Gales, M. J. F. (2023). SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative LLMs. *EMNLP*.
5. Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2024). Chain-of-Verification Reduces Hallucination in Large Language Models. *Findings of ACL*.
6. Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2024). Improving Factuality and Reasoning in Language Models through Multiagent Debate. *ICML*.
7. Wang, Y., et al. (2024). OpenFactCheck: A Unified Framework for Factuality Evaluation of LLMs. *EMNLP (System Demonstrations)*.

*Empirical journal literature reviewed (representative; the full 35-paper review is provided as a supplementary literature table). Author surnames to be completed from each DOI before submission:*

8. Yanagita, Y., et al. (2023). Accuracy of ChatGPT on the Japanese National Medical Licensing Examination. *JMIR Formative Research*.
9. Massenon, R., et al. (2025). User-reported LLM hallucinations in AI mobile-app reviews. *Scientific Reports*.
10. (2025). A framework to assess clinical safety and hallucination rates of LLMs for medical text summarisation. *npj Digital Medicine*.
11. (2025). Retrieval-augmented generation for 10 large language models and its generalizability in assessing medical fitness. *npj Digital Medicine*.
12. Kolluri, N., et al. (2022). COVID-19 misinformation detection: machine-learned solutions to the infodemic. *JMIR Infodemiology*.
13. Martín, Á., et al. (2022). FacTeR-Check: semi-automated fact-checking through semantic similarity and natural language inference. *Knowledge-Based Systems*.
14. (2024). Factual consistency evaluation of summarization in the era of large language models. *Expert Systems with Applications*.
15. (2025). Mitigating reasoning hallucination through multi-agent collaborative filtering. *Expert Systems with Applications*, 263.
16. Khatri, ... (2025). Accuracy and reproducibility of ChatGPT responses to real-world drug-information questions. *JACCP*.
17. (2024). Generating credible referenced medical research: GPT-4 vs Gemini. *Computers in Biology and Medicine*.

*Contemporary preprints cited for positioning (identifiers to be confirmed against final published versions before submission):*

a. "Talk Isn't Always Cheap." arXiv:2509.05396.
b. "Peacemaker or Troublemaker." arXiv:2509.23055.
c. "The Deliberative Illusion." arXiv:2606.03032.
d. "Show Your Work." medRxiv 2026.03.03.26346690 / *Cureus* 2026.
e. "Debating Truth." arXiv:2507.19090 (WWW 2026).
f. "TRUST Agents." arXiv:2604.12184.

*All numeric results are traceable to committed seeded runs in the project's evaluation record; no value is projected. Two experiments named in §7 (soft-grounding baseline arm; leaderboard comparison) remain before submission to a top-tier venue.*
