---
title: "A Hard Verbatim-Evidence Gate as the Precondition for Multi-Agent Claim Verification: Design, Deployment, and Empirical Boundary Conditions"
author:
  - "Jay Gautam^[Department of Computer Science and Engineering (Artificial Intelligence and Machine Learning), P P Savani University, Surat, India. Corresponding author: jaygautam561@gmail.com. Source code, run traces, and evaluation record: https://github.com/jaygautam-creator/Aletheia]"
  - "Rahul Kumar^[Assistant Professor, Department of Computer Science and Engineering, P P Savani University, Surat, India.]"
date: "September 2026"
abstract: |
  Multi-agent large language model (LLM) pipelines verify claims by having model instances critique one another, but agreement reached through opinion carries no guarantee that any evidence supports it, and prompt-enforced grounding reduces unsupported assertion without preventing it. This study evaluates a structural alternative: a verdict may be Supported or Contradicted only if it quotes a span that pipeline code finds verbatim in the retrieved evidence; otherwise it is rewritten to Unverifiable. The gate was built into Aletheia, a deployed LangGraph verification service, and compared with a single-LLM baseline and an otherwise identical ungrounded ablation on SciFact and FEVER, using one frozen corpus, seeded stratified samples of 100 claims, and paired significance tests. On the deployed model the grounded arm ties the baseline on accuracy (79.0 versus 79.0 percent) and leads on catch rate (96.6 versus 93.1 percent) and false agreement (6.1 versus 10.5 percent), but neither interval excludes zero. On an 8-billion-parameter model the catch-rate gain is significant: 82.8 versus 60.3 percent, +22.4 points, 95 percent confidence interval [+12.1, +33.3]. On FEVER's paraphrased claims the ungrounded ablation is significantly more accurate (85.0 versus 77.0 percent). Re-checked from traces, 51 of 51 asserted FEVER verdicts are verbatim-backed, yet five are wrong: the gate guarantees a faithful quotation, not a correct inference. Structural grounding buys accuracy for weak models and auditability for strong ones --- a boundary condition, not a leaderboard win.
keywords: "automated claim verification; large language models; hallucination mitigation; multi-agent systems; retrieval-augmented generation; evidence grounding; reproducible evaluation; false agreement"
geometry: "a4paper, margin=1.9cm"
fontsize: 10pt
linestretch: 1.0
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
numbersections: true
header-includes:
  - \usepackage{etoolbox}
  - \usepackage{tikz}
  - \usetikzlibrary{arrows.meta,positioning,shapes.geometric}
  - \usepackage{float}
  - \floatplacement{figure}{H}
  - \AtBeginEnvironment{longtable}{\footnotesize}
  - \setlength{\parskip}{0.35em}
  - \setlength{\LTpre}{0.6em}
  - \setlength{\LTpost}{0.6em}
---

**Index Terms** --- automated claim verification, large language models, hallucination mitigation, multi-agent systems, retrieval-augmented generation, evidence grounding, reproducible evaluation, false agreement.

**Reference confidence legend.** Every entry in the reference list carries a verification tag: **[V]** verified against its record of origin (DOI registry, arXiv, or the publisher's page); **[L]** likely real, bibliographic details still to be confirmed; **[U]** could not verify. In the September 2026 revision every entry is **[V]**; no claim in this paper rests on an **[L]** or **[U]** source. The registry and the corrections made while building it are in Appendices D and E.

**Terminology.** A *point* is a percentage point. *CI* is a 95 percent confidence interval. The grounded arm exists in four successive versions, V1--V4 (Section 6.7); every result below is labelled with the version that produced it.

# Introduction

A large language model deployed for medical question answering produced hallucinated references at a measurable rate in a controlled clinical review [8], [19], and a clinician-annotation framework over 12,999 sentences of LLM-generated medical summaries measured a hallucination rate of 1.47 percent and an omission rate of 3.45 percent [10]. Those numbers are small in aggregate and unacceptable individually: the failure is not a visibly broken answer but a fluent, confidently stated one that no source supports.

Automated claim verification is where this failure is most costly. A system that labels a false claim *Supported*, or asserts more than its retrieved evidence licenses, does not merely fail to catch misinformation; it manufactures it, in the same confident register it uses when correct. The user receives no signal separating a trustworthy verdict from a fabricated one.

Two mitigation strategies dominate. The first is retrieval-augmented generation (RAG), which grounds generation in retrieved passages and consistently reduces hallucination, in some clinical configurations to near zero [11], [12], [13]. The second is multi-agent critique, in which several model instances debate or review one another's output to improve factuality [6]. Each has a structural weakness. RAG's grounding is enforced by instruction --- the model is asked to use only the retrieved passages --- so a model may still contradict, over-reach beyond, or ignore the evidence it was given. Multi-agent critique inherits a distinct failure mode that a recent cluster of studies has characterised directly: debating agents exhibit sycophancy, premature convergence, and consensus on incorrect answers [23], [24], [25]. Because the exchanged objects are opinions rather than evidence, agreement between agents carries no independent guarantee of correctness.

**Problem statement.** No mechanism in current multi-agent verification pipelines structurally prevents a verdict from affirming a claim that it cannot support with a quotation from the evidence, and no empirical study quantifies what such a mechanism costs in accuracy, latency, and tokens.

**Motivation.** Deployment of LLM verification into consequential domains is already under way, as the medical literature reviewed in Section 2 shows, so the cost of a confident wrong verdict is being incurred in practice. At the same time base-model capability is rising quickly, which makes the *conditions* under which a reliability mechanism pays for itself a moving target: a safeguard that is essential at one model scale may be overhead at the next.

**Research gap.** A structured review of 35 original empirical journal articles on LLM factuality, hallucination, and claim verification (Section 2) shows that grounding is enforced softly [11], [12], [13]; that systems are overwhelmingly single-model, with multi-agent LLM verification appearing rarely in journal work [17] and its false-agreement risk unexamined; and that the latency and cost of the reliability mechanism are almost never reported [14], [15], [16]. Examination of the closest technical antecedents, which sit mostly in conference and preprint venues, shows that hard verbatim-quote requirements exist for single-model classification [26], while multi-agent claim verification grounds evidence through LLM-judgment moderation [27], calibrated confidence [28], or natural language inference (NLI) scoring [29] --- never a mechanical string check. The gap is therefore methodological: *no empirical study evaluates a hard, mechanically verified verbatim-evidence gate as the structural precondition for multi-agent claim verification, together with its catch-rate, false-agreement, accuracy, latency, and cost trade-offs across model scales and domains.*

**Research objectives.**

1. To design and deploy a multi-agent verification pipeline in which a mechanical verbatim-substring match is a hard precondition for any affirmative or contradictory verdict.
2. To measure that pipeline's hallucination-catch rate, false-agreement rate, verification accuracy, latency, and token cost against a single-LLM baseline and an ungrounded ablation on the same claims, evidence, and model.
3. To explore whether the measured effects persist across base-model scale (8 billion to 550 billion parameters) and across two claim domains.
4. To establish, from run traces, whether the gate's mechanical guarantee holds exactly on every asserted verdict.

**Research questions.**

- **RQ1.** Does an evidence-grounded multi-agent pipeline catch measurably more hallucinations than a single LLM on the same claims?
- **RQ2.** Does requiring a quoted verbatim span lower the false-agreement rate relative to an otherwise identical ungrounded multi-agent arm?
- **RQ3.** What latency and token overhead does the gate impose?
- **RQ4 (exploratory).** How do the effects in RQ1--RQ3 vary with base-model strength and with claim domain?

**Contributions.**

1. *(Artifact/tool)* Aletheia, a deployed, publicly runnable verification service in which the verbatim-span check is executed in pipeline code rather than requested in a prompt, together with a seeded, reproducible evaluation harness and committed per-claim traces.
2. *(Methodological)* A structural evidence gate that makes a mechanical verbatim-substring match the precondition for the Verifier's affirmative or contradictory verdict within a multi-agent pipeline, with an ablation that removes exactly the span discipline --- to the authors' knowledge, after a full-text search of the closest candidates, the first such construction evaluated inside a multi-agent verification structure.
3. *(Empirical)* A boundary condition measured at paired, powered sample size in two domains: the gate's accuracy contribution is significant and positive for a weak base model and zero for the deployed model, it costs accuracy on paraphrase-heavy claims, and its catch-rate advantage over a single LLM is significant for the weak model and on FEVER. An exploratory sweep to 550B suggests the accuracy contribution turns negative for strong models.
4. *(Conceptual)* An explicit separation of two guarantees --- *no unsupported assertion* versus *correct entailment* --- extending an observation made for single-model classification [26] to multi-agent verification, and demonstrated by an error class in which the model quotes the evidence exactly and still reasons incorrectly.

**Paper organisation.** Section 2 reviews the literature and derives the gap. Section 3 formalises the problem and its scope. Sections 4 and 5 state objectives, research questions, and hypotheses. Section 6 details the methodology, Section 7 the proposed system and its novelty claim, and Section 8 the experimental setup. Section 9 reports results, Section 10 interprets them, Section 11 states limitations and threats to validity, Section 12 concludes, and Section 13 derives future work from specific limitations. Appendices A--K contain the research plan, gap statement, contribution summary, source registry, citation notes, a simulated peer review, a vulnerability report, an improvement roadmap, the outstanding experiments, the quality-assurance record, and alternative titles.

# Literature Review and Related Work

The thematic review draws on 35 original empirical journal articles, deliberately excluding reviews, meta-analyses, and conference proceedings, so that each finding rests on a peer-reviewed empirical study. Because the mechanism at issue is recent, its closest technical antecedents appear mostly in conference proceedings and preprints; these are reviewed separately below, and the gap statement rests on both bodies of evidence. The review is organised by theme rather than by paper.

## Theme 1: Measuring factual accuracy and citation reliability

The first line treats factuality as a benchmarking problem. GPT-4 scored 81.5 percent against 42.8 percent for GPT-3.5 on 292 Japanese National Medical Licensing Examination questions [8]; comparative studies contrast citation credibility between GPT-4 and Gemini on medical references [19]; and expert evaluation of repeated drug-information queries finds accuracy and reproducibility to vary within a single domain [18]. These studies establish that the problem is real and measurable in deployment-relevant settings.

*Critical analysis.* The methodological strength is expert ground truth; the weakness is that measurement yields no mechanism. A benchmark score describes a model's aggregate reliability but cannot indicate at inference time which particular answer is the unreliable one. Every study in this theme is single-domain and single-model, and none reports the cost of a corrective mechanism, because none proposes one.

## Theme 2: Detecting and characterising hallucination

The second line detects unsupported output rather than scoring correctness. A taxonomy built from three million app-store reviews across 90 applications found factual errors to constitute 38 percent of user-reported hallucinations [9]; a clinician-annotation framework quantified hallucination and omission rates in medical summarisation [10]; and LLM-based metrics for factual consistency in summarisation improve correlation with human judgment over earlier automatic measures [16]. Reference-free approaches detect hallucination without retrieving evidence, by scoring the consistency of multiple sampled generations [4] or by answering self-generated verification questions from the model's own parameters [5]. Evaluation work outside the journal corpus has standardised factual-consistency scoring: NLI and question-answering scorers perform strongly and complementarily across eleven datasets [37], and a unified alignment function trained on 4.7 million examples generalises across 22 evaluation sets [38].

*Critical analysis.* This theme supplies the field's vocabulary and measurement instruments, and its reference-free methods need no corpus. That independence is also the limitation: a detector that consults only the model cannot distinguish a confident falsehood from a confident truth on a matter the model was trained to be wrong about. The consistency scorers [37], [38] do consult evidence, but they return a graded score to which a threshold must be applied --- a soft check. The open question is whether unsupported assertion can be *prevented* structurally rather than scored after the fact.

## Theme 3: Retrieval-augmented mitigation

The third line grounds generation in retrieved evidence. RAG evaluated across ten LLMs for medical fitness assessment reached 96.4 percent with GPT-4 and no observed hallucination [11]; a two-layer RAG architecture improved grounding in low-resource medical question answering [12]; and a multilingual RAG verifier improved cross-lingual misinformation detection [13]. Citation-generation benchmarks show the limit of the approach: even the best evaluated models lacked complete citation support 50 percent of the time on one long-form dataset [36].

*Critical analysis.* Retrieval demonstrably reduces hallucination, and the effect replicates across models, languages, and clinical subdomains. Its weakness is enforcement: in every system in this theme the instruction to rely on retrieved passages is delivered in the prompt, so compliance is a behaviour the model exhibits with high probability rather than a property the system guarantees. None of these studies verifies mechanically that a produced assertion corresponds to retrieved text, and none reports the latency or token cost of the retrieval layer.

## Theme 4: Automated verification, multi-agent critique, and its failure modes

The fourth line labels claims against evidence. FEVER established large-scale fact extraction and verification over Wikipedia [1]; SciFact introduced expert scientific claims over biomedical abstracts with an extractive rationale-selection baseline [2], later improved by weak supervision and full-document context [3]. Evidence-linked pipelines combine semantic-similarity retrieval with NLI [14], while content-based detection uses pretrained language models over thematic, sentiment, and stance cues [15], graph-augmented transformer ensembles [22], or multimodal attention fusion [21]; at scale, machine-learned pipelines reached 99.1 percent on a COVID-era misinformation corpus [20]. Multi-agent approaches appear rarely in journal work: collaborative filtering across agents reduces reasoning hallucination [17], and debate among model instances improves factuality [6]. A 2025--2026 cluster of studies documented the countervailing risk, reporting sycophancy, premature consensus, and false agreement among debating agents [23], [24], [25].

*Critical analysis.* Benchmarks in this theme define the task and supply gold labels, but their leading systems are supervised classifiers that emit a label without binding it to a checkable span, and the detection subfield optimises accuracy on recurring corpora with limited attention to explanation [21], [22]. The multi-agent subfield is where the literature disagrees most sharply: [6] and [17] report that agent interaction improves factuality, while [23], [24], [25] report that the same interaction produces correlated error. The two findings are reconcilable if the *content* of the exchange determines the outcome --- the variable no study in this theme manipulates structurally.

## Direct technical antecedents

Two lines sit closest to the present mechanism. Hard, mechanically checked quotation exists for single models: Windisch et al. required three flagship models to return a verbatim supporting quote when classifying the eligibility scope of 200 oncology trial abstracts, validated each quote as an exact substring after whitespace normalisation, and found that mechanically valid quotes were judged semantically supporting in only 48.0 to 78.8 percent of evidence-bearing predictions [26]. That study is a single-model, label-only versus label-plus-quote comparison, with no multi-agent structure, aggregator, or deployed baseline. Conversely, multi-agent debate for claim verification is an active subfield, but its grounding is soft: a moderator that weighs the evidential strength of conflicting arguments [27], a verifier agent that produces verdicts with calibrated confidence [28], or NLI and token-overlap citation scoring [29]. Hard gates outside text quotation --- Lean4 kernel-checked formal proofs [30] and constraint-satisfaction structural consistency [31] --- do not operate on natural-language evidence spans, and tool provenance mediates agreement in [32] without a string-level check. On evaluation practice, joint reporting of accuracy, latency, and cost has precedent [7], though without catch-rate or false-agreement axes.

## Comparison of representative related work

| Author(s) / Year | Approach | Dataset / Area | Metrics | Key finding | Limitation |
|:--|:--|:--|:--|:--|:--|
| Thorne et al., 2018 [1] | Supervised extract-and-verify | FEVER, Wikipedia | Label accuracy, FEVER score | Large-scale verification is learnable | Single supervised label; no span guarantee |
| Wadden et al., 2020 [2] | Extractive rationale selection | SciFact abstracts | Label and rationale F1 | Rationale selection aids scientific verification | Single model; no mechanical span check |
| Wadden et al., 2022 [3] | Weak supervision, full-document context | SciFact | Label and rationale F1 | Context and weak supervision improve accuracy | No cost or latency reporting |
| Manakul et al., 2023 [4] | Sampling-consistency detection | Reference-free generation | Detection AUC | Hallucination detectable without evidence | No evidence retrieved; detects, does not prevent |
| Du et al., 2024 [6] | Multi-agent debate | Reasoning and factuality tasks | Task accuracy | Debate improves factuality | Opinion-only exchange; consensus unguarded |
| Ke et al., 2025 [11] | RAG across ten LLMs | Medical fitness assessment | Accuracy, hallucination rate | 96.4 percent, no observed hallucination | Grounding prompt-enforced; single domain |
| Martín et al., 2022 [14] | Similarity retrieval plus NLI | Spanish COVID claims | F1, retrieval quality | Evidence-linked verification is feasible | Not generative; domain- and language-bound |
| Shi et al., 2025 [17] | Multi-agent collaborative filtering | Reasoning and QA sets | Hallucination rate | Cross-checking lowers hallucination | Compute-heavy; agreement not gated |
| Windisch et al., 2026 [26] | Verbatim quote validated as exact substring | 200 oncology trial abstracts | Coverage, macro-F1, quote validity | Valid quotes often not semantically supporting | Single-model classification only |
| He et al., 2025 [27] | Multi-agent debate with moderator | Claim verification | Accuracy | Debate aids verification | Soft, LLM-judged grounding |
| Bulusu Venkata et al., 2026 [28] | Multi-agent verification with calibrated confidence | Fake-news claims | Accuracy, calibration | Agent collaboration aids explainable verification | No verbatim-match step |
| **This work** | **Hard verbatim gate as precondition for a verdict in a multi-agent pipeline** | **SciFact and FEVER, frozen corpus** | **Accuracy, catch rate, false agreement, latency, tokens** | **Guarantee holds on every asserted verdict; accuracy effect scale- and domain-dependent** | **No soft-grounding arm; single seeded run per configuration** |

## Synthesis and derived gap

Across the four themes one pattern recurs: *reduction without guarantee*. Theme 1 measures the problem but supplies no mechanism; Theme 2 detects or scores unsupported output after it exists; Theme 3 reduces it probabilistically through prompt-enforced grounding; Theme 4 introduces agent interaction whose benefit [6], [17] and whose correlated-error risk [23], [24], [25] are both documented, with no structural control over which occurs. The body of work shares three methodological weaknesses: enforcement is behavioural rather than mechanical, systems are predominantly single-model, and the latency and token cost of the reliability mechanism is essentially unreported. The technical antecedents close part of the remaining space --- mechanically checked quotation exists for single models [26], multi-agent verification exists with soft grounding [27], [28] --- and leave their intersection unoccupied. That intersection is the gap this paper addresses.

# Research Problem

**Semi-formal definition.** Let $c$ be a claim, $E$ the evidence retrieved for $c$ from a fixed corpus $C$, and $V \in \{\textit{Supported}, \textit{Contradicted}, \textit{Unverifiable}\}$ a verdict produced by a verification system. Let $s$ denote a span of text emitted alongside $V$. The system studied here enforces the constraint

$$V \in \{\textit{Supported}, \textit{Contradicted}\} \implies \eta(s) \sqsubseteq \eta(E),$$

where $\eta$ is a fixed, auditable normalisation (whitespace collapsing and, from version V4, a closed set of punctuation folds) and $\sqsubseteq$ denotes contiguous substring containment. Any verdict violating the constraint is rewritten to *Unverifiable* by pipeline code before it is returned. The research problem is to determine the empirical consequences of enforcing this constraint mechanically, relative to not enforcing it, holding claim, evidence, and model fixed.

**Scope --- included.** Claim-level verification against a frozen, versioned corpus; a single-LLM baseline and an ungrounded ablation; two benchmark domains; base models from 8B to 550B parameters; and free-tier deployment of the same Verifier and gate code used for evaluation.

**Scope --- explicitly excluded.** (i) The live Wikipedia and web fallback, which exists in the deployed product for claims outside the corpus but never contributes to a reported number; (ii) multimodal claim intake from images and documents; (iii) verification against a user-supplied document; (iv) non-English claims; (v) adversarial real-world misinformation; (vi) medical advice, diagnosis, or treatment recommendation of any kind, which the system refuses by design; (vii) training or fine-tuning, since every arm uses the same frozen instruction-tuned model through an API; and (viii) leaderboard competition against supervised state-of-the-art systems, which is discussed as a limitation rather than attempted.

**Assumptions.** (A1) Gold benchmark labels are correct, subject to the caveat in Section 9.3 on SciFact's evidence-set-relative *NotEnoughInfo* (NEI) definition. (A2) A substring match under $\eta$ is a sound test of quotation, i.e. it admits no fabricated quote; it is not assumed to be a test of correct entailment. (A3) Latency measured on a shared free-tier provider is comparable across arms only within one run, since all arms are measured under the same conditions at the same time.

**Variables.** The *independent* variable is the verification architecture (baseline, ungrounded, grounded). *Dependent* variables are verification accuracy, hallucination-catch rate, false-agreement rate, latency percentiles, and tokens per query. *Controlled* variables are the claim set, the retrieved evidence, the base model, decoding temperature (0.0 throughout), the sampling seed, and the corpus state. *Moderating* variables, examined in Sections 9.4, 9.5, and 9.7, are base-model scale and claim domain. The grounded-arm version (Section 6.7) is a further variable that is held fixed within every comparison and labelled across them.

# Research Objectives

**O1 --- Construct.** Implement a multi-agent verification pipeline in which the constraint of Section 3 is enforced in code, verified by unit tests that assert a fabricated span is downgraded, and deployed as a publicly reachable service on free-tier infrastructure. *Measurable by:* the deployed endpoint and a passing test suite covering the verdict contract.

**O2 --- Quantify.** Measure verification accuracy, hallucination-catch rate, false-agreement rate, latency at the 50th, 95th, and 99th percentiles, and tokens per query for three architectures judging an identical seeded sample of 100 SciFact claims, with paired significance testing on per-claim predictions. *Measurable by:* a reproducible results table with confidence intervals and test statistics.

**O3 --- Explore.** Repeat the comparison across base-model scales and on a second, adversarially chosen domain, and report the direction and, where powered, the significance of each effect. *Measurable by:* per-scale and per-domain deltas with their intervals.

**O4 --- Audit.** Verify from run traces that every asserted verdict is backed by a span appearing verbatim in its retrieved evidence, and classify every residual error by cause. *Measurable by:* the proportion of asserted verdicts that survive independent re-checking, and an error decomposition by category.

# Research Questions and Hypotheses

**RQ1 --- Catch rate.** Answered by the paired per-claim catch-rate delta between the grounded arm and the baseline, with a percentile-bootstrap CI.

**RQ2 --- False agreement.** Answered by the grounded-versus-ablation delta, where the ablation prompt shares the grounded prompt's role and verdict definitions and omits only the span-discipline block (Section 6.6).

**RQ3 --- Cost.** Answered by per-arm latency percentiles and mean tokens per query recorded in the same runs.

**RQ4 --- Moderation by scale and domain.** Answered by comparing the deltas across base models and between SciFact and FEVER.

**Hypotheses.** H1--H3 were committed to the project's evaluation record on 26 June 2026, before any benchmark run, and are stated here as written there. H2 originally named "opinion-only multi-agent debate" as its comparator; on 2 July 2026, before the first Phase 3 run, that comparator was operationalised as the ungrounded ablation arm, and the wording below is that version.

- **H1 (catch rate).** Aletheia achieves a higher hallucination-catch rate than a single-LLM baseline on the same benchmark. Tested as $H1_0$: paired catch-rate delta $= 0$ against $H1_a$: delta $> 0$.
- **H2 (grounding reduces false agreement).** Requiring quoted-span evidence lowers the false-agreement rate compared with an otherwise-identical multi-agent arm whose verdicts are opinion-only (no span discipline). Tested as $H2_0$: paired false-agreement delta $= 0$ against $H2_a$: delta $< 0$.
- **H3 (acceptable cost).** The reliability gains come at a quantified, defensible latency and per-query cost overhead. H3 is a measurement objective: no acceptability threshold was registered, so the overhead is reported for the reader to judge.

RQ4 is **exploratory**. The scale sweep is under-powered by design (n = 19 to 30), no hypothesis is tested on it, and it is reported for direction and mechanism only.

# Methodology

## Research design

The study is **design science with an embedded quantitative experiment**. The design-science component builds an artifact --- a deployed verification service --- whose central design decision is the mechanical evidence gate. The experimental component evaluates the artifact against two counterfactual architectures on identical inputs. A purely quantitative framing was rejected because the contribution includes a system whose deployability is part of the claim; a purely design-science framing was rejected because the central assertion is empirical and requires significance testing.

## System architecture

```{=latex}
\begin{figure}[H]
\centering
\footnotesize
\begin{tikzpicture}[
  >={Stealth[length=2mm]},
  node distance=5mm and 6mm,
  stage/.style={draw=black!45, rounded corners=1.5pt, minimum height=7.5mm,
                minimum width=19mm, align=center, inner sep=2pt},
  llm/.style={stage, fill=blue!6},
  gate/.style={draw=teal!75!black, very thick, rounded corners=1.5pt,
               minimum height=7.5mm, minimum width=27mm, align=center, inner sep=2pt},
  store/.style={draw=black!35, dashed, rounded corners=1.5pt, minimum height=6.5mm,
                align=center, inner sep=3pt},
  term/.style={draw=blue!55!black, rounded corners=6pt, minimum height=7mm, align=center, inner sep=3pt},
  lbl/.style={font=\scriptsize, text=black!62}]

\node[term] (q) {Claim /\\ query};
\node[llm, right=of q] (in) {Intake guard\\ \scriptsize optional};
\node[stage, right=of in] (re) {Retriever\\ \scriptsize optional; RRF};
\node[llm, right=of re] (ge) {Generator\\ \scriptsize atomic claims};
\node[llm, right=of ge] (ve) {Verifier\\ \scriptsize verdict + span};

\node[store, above=5mm of re] (db) {PostgreSQL + pgvector\\ \scriptsize frozen, versioned corpus};

\node[gate, below=16mm of ve] (gt) {\textbf{Evidence gate}\\ \scriptsize\texttt{grounded\_against(evidence)}};
\node[stage, left=8mm of gt] (ag) {Aggregator\\ \scriptsize + disagreements};
\node[stage, left=of ag] (gd) {Guardrail\\ \scriptsize advisory only};
\node[term, left=of gd] (out) {Answer +\\ verdicts};

\draw[->] (q) -- (in);
\draw[->] (in) -- (re);
\draw[->] (re) -- (ge);
\draw[->] (ge) -- (ve);
\draw[<->] (re) -- (db);
\draw[->] (ve) -- (gt);
\draw[->] (gt) -- (ag);
\draw[->] (ag) -- (gd);
\draw[->] (gd) -- (out);

\node[lbl, right=1.5mm of gt, text width=27mm] {span found\\ verbatim $\Rightarrow$ verdict stands};
\node[lbl, below=5mm of gt.south, anchor=north] {no match $\Rightarrow$ verdict rewritten to \emph{Unverifiable}, span dropped};
\end{tikzpicture}
\caption{The Aletheia pipeline. Shaded stages call a language model; the Retriever,
evidence gate, Aggregator, and Guardrail are ordinary code. The gate is executed in
pipeline code, and no prompt, confidence score, or secondary model judgement can bypass
it. The benchmark exercises the Retriever, Verifier, and gate only (Section 6.3).}
\end{figure}
```

The pipeline is orchestrated as a LangGraph state machine whose stages execute in the following order.

1. **Intake guard (optional).** A deterministic prompt-injection scan followed by an LLM scope classifier admits or refuses the query. It is enabled in the deployed service and disabled in the benchmark. A refusal returns a reason, and the Generator and Verifier never run.
2. **Retriever (optional).** Hybrid semantic and lexical search over a frozen PostgreSQL corpus with the pgvector extension, fused by Reciprocal Rank Fusion (RRF) [34]. It runs only when the caller supplies no evidence of their own.
3. **Generator.** Produces a candidate answer and decomposes it into atomic claims.
4. **Verifier.** Judges each claim against the evidence under the span discipline, returning a verdict, a span, and a justification as strict JSON.
5. **Evidence gate.** Pipeline code calls `grounded_against(evidence)`, which tests the span for containment under $\eta$ and rewrites any failing verdict to *Unverifiable*, dropping its span and recording the downgrade.
6. **Aggregator.** Collects verdicts into a final answer with an evidence-derived confidence signal and an explicit list of disagreements, which are surfaced rather than resolved away.
7. **Guardrail.** Attaches an advisory and a standing disclaimer. It runs last, is advisory, and never edits a verdict.

Grounding is therefore structural rather than aspirational: the model is not merely instructed to quote honestly; an assertion whose quotation cannot be found is discarded.

## What the benchmark exercises, and in what sense it is multi-agent

The benchmark scores the Verifier and the gate, not the whole pipeline. For each claim the harness retrieves evidence once, shares it across all arms, and issues **exactly one model call per claim per arm**. The Generator is held out because benchmark claims are already atomic and decomposing them would blur the alignment between claim and gold label; the intake guard, Aggregator, and Guardrail are not on the scored path. The Verifier and gate code are the same code the deployed service runs, so the reported numbers describe the deployed verification step, not an evaluation-only reimplementation of it.

"Multi-agent" in this paper therefore refers to the deployed pipeline, in which a Generator's claims are admitted only through an independent Verifier whose affirmation must pass the gate. It does not refer to multi-round debate: no arm in the benchmark exchanges messages between agents. The ablation is called "multi-agent, ungrounded" because it uses the Verifier's per-claim critic role without the span discipline; the baseline uses a shorter holistic judging prompt. Section 11 returns to what this does and does not license.

## Dataset and data sources

**SciFact** [2] supplies expert-written scientific claims labelled against biomedical abstracts; its 5,183-abstract corpus was ingested, yielding 15,411 chunks. It was selected because its claims can be grounded in a curated biomedical corpus; its labels map directly onto the verdict space (*SUPPORT* to *Supported*, *CONTRADICT* to *Contradicted*, NEI to *Unverifiable*); and it ships its own evidence corpus, which contains every abstract cited by all 300 claims of the `dev` split.

**FEVER** [1] supplies open-domain claims over Wikipedia and was chosen because it is adversarial for the mechanism under test: FEVER claims are crowdworker *paraphrases* of source sentences rather than near-quotations, so verbatim grounding is stressed where it is weakest. Ingesting the full 5.4-million-page dump would violate the fixed-corpus rule and the free-tier constraint, so a deterministic, seeded slice of approximately 5,000 documents was built, comprising every sampled claim's evidence pages plus seeded distractors.

*Known dataset limitations.* SciFact's NEI label is defined relative to its own annotated evidence set, whereas the system retrieves from the full corpus; a verdict scored as an unsupported assertion may therefore have genuine but uncited support, which makes the false-grounding figures upper bounds (Section 9.3). Both benchmarks are public and predate the evaluated models, so pretraining contamination cannot be excluded; the mitigation is to report relative gaps between arms rather than absolute scores. FEVER's Wikipedia text ships in Penn Treebank tokenisation, a property that materially affected results (Section 9.7).

## Data preprocessing

Corpus documents are split into overlapping, word-aligned chunks of at most 1,000 characters with approximately 150 characters of overlap. Each chunk is embedded and stored with its source identifiers so that any span can be resolved to its document. For FEVER, Penn Treebank markup (`-LRB-`, `-RRB-`, space-separated punctuation) is folded to plain text at ingestion, in both page bodies and page titles. No class rebalancing is applied, because the label distribution is preserved deliberately by stratified sampling, and missing data is not imputed: a claim whose cited evidence is absent from the corpus would be detected by the coverage check and scored as *Unverifiable*.

At match time, both the candidate span and the evidence pass through one shared normalisation function, $\eta$. From version V4 it collapses whitespace and folds a closed set of interchangeable glyphs --- middle dot, bullet, en dash, em dash, minus sign, non-breaking hyphen, directional quotation marks, and the no-break space --- to ASCII equivalents; before V4 it collapsed whitespace only. There is no fuzzy matching and no Unicode compatibility normalisation, every word must still appear, and a span stitched together from separate passages with an ellipsis fails containment by construction. The grounding check and the interface's span-to-source resolution call the same function, so the tolerance is defined in exactly one place.

## Algorithms and models

**Retrieval.** For a query $q$, a semantic branch ranks chunks by cosine similarity between query and chunk embeddings, and a lexical branch ranks by keyword match. Each branch returns a candidate pool of 20, and the pools are fused by RRF [34], which scores each chunk $d$ as

$$\mathrm{RRF}(d) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(d)},$$

with $k = 60$ and $R$ the set of branch rankings. The top 8 fused chunks are returned as evidence. RRF was chosen over score normalisation because it needs no calibration between two incommensurable score scales.

**Verification.** The Verifier receives one claim and the evidence and must return strict JSON with a verdict, an optional span, and a justification. In its current form (V4) the prompt's span-discipline block contains: the requirement to quote an exact span for *Supported* or *Contradicted*; a two-sided *span-sufficiency test* (assert only when the span, read alone, settles the claim, and do not retreat to *Unverifiable* when it plainly does); an instruction to judge meaning rather than wording, since only the quote must be verbatim; and a rule that the span be one continuous passage. The response is parsed into a validated object whose constructor rejects an asserted verdict with an empty span and an *Unverifiable* verdict that carries one, after which the gate applies the containment test.

**Ablation arm.** The ungrounded prompt shares the grounded prompt's role statement and three verdict definitions and omits the entire span-discipline block; its verdicts are accepted as returned, with no containment check. The sufficiency test is deliberately not mirrored into the ablation, because reasoning about whether a quoted span settles a claim is itself part of the span discipline; a unit test guards this split. The H2 comparison therefore measures *span discipline plus gate* against neither. It does not separate the effect of the prompt block from the effect of the mechanical check (Section 11).

**Hyperparameters.** Decoding temperature is 0.0 for every arm and call. Retrieval parameters (pool 20, top-$k$ 8, RRF constant 60) are fixed defaults declared in configuration. No grid, random, or Bayesian search was conducted over prompt or retrieval hyperparameters, because a search optimising one arm would destroy the property that arms differ only in architecture.

## Grounded-arm versions

The grounded arm's prompt and gate were revised three times during the study, each change additive and confined to the grounded arm. The baseline and ablation prompts were unchanged throughout, and the baseline and ablation arms reproduce identical accuracy, catch rate, and false agreement across the two 8B runs of Table 3 --- a direct check that the controls did not drift.

| Version | Change to the grounded arm | In code from | Runs reported with it |
|:--|:--|:--|:--|
| V1 | Original span-quoting prompt; whitespace-only $\eta$ | 26 Jun 2026 | 8B SciFact n = 100 (3 Jul); exploratory scale sweep; seed-13 control |
| V2 | + two-sided span-sufficiency test | 11 Jul 2026 | 8B SciFact n = 100 (19 Jul); seed-13 treatment; 70B and 550B re-runs |
| V3 | + "judge meaning, not wording" instruction | 20 Jul 2026 | 8B SciFact n = 30 spot-check (22 Jul) |
| V4 | + single-continuous-span rule; punctuation fold added to $\eta$ | 24 Jul 2026 | FEVER n = 100 (25 Jul); deployed-model SciFact n = 100 (3 Aug) |

V4 is the deployed system and the system described in Section 7. Comparisons are made only within a version, except where a version change is itself the object of study (Sections 9.2 and 9.6).

## Tools and technologies

| Layer | Technology |
|:--|:--|
| Language and runtime | Python 3.12 or later; TypeScript (Next.js App Router) |
| Backend service | FastAPI with Uvicorn, asynchronous throughout |
| Agent orchestration | LangGraph 1.2 or later |
| Vector store | PostgreSQL with pgvector (Python client 0.5 or later), via SQLAlchemy 2.0 asynchronous and Alembic migrations |
| Embeddings | `BAAI/bge-small-en-v1.5` [33] at 384 dimensions, run locally through fastembed ONNX (CPU only) |
| LLM access | Provider-agnostic client over Google Gemini, Groq, and OpenRouter, with retry and back-off; cross-provider fail-over disabled for benchmark runs |
| Evaluation | Purpose-built harness (`aletheia.evaluation`) with seeded sampling, trace logging, and offline error analysis |
| Quality tooling | uv, ruff, mypy, pytest; GitHub Actions continuous integration |
| Deployment | Vercel (frontend), Render (backend), Neon (PostgreSQL), all free tier |

## Experimental protocol

No model is trained, so there is no train/validation/test split: every arm is a frozen instruction-tuned model accessed through an API, and the benchmark's development split serves as an evaluation set. Subsets are drawn by **seeded, gold-label-stratified sampling without replacement**, with allocation proportional to each label's share, so that the same claim file, sample size, and seed always reproduce the same subset. Before any model call the runner computes **corpus coverage** --- the fraction of sampled claims whose every cited document is present in the frozen corpus --- and warns below 95 percent.

Two baselines are compared. The **single-LLM baseline** uses the same model, evidence, and corpus access policy and differs only in verification architecture. The **ungrounded ablation** keeps the Verifier's per-claim critic role and removes only the span discipline and the gate. Reporting order is always baseline, ungrounded, grounded.

Runs are executed once per configuration with a fixed seed (seed 7 for headline runs, seed 13 for the held-out verifier A/B). The harness supports repeated runs aggregated as mean and standard deviation, but repeats at n = 100 were not affordable on free-tier quotas (Section 11). A provider error on any item excludes that item from **every** arm, so pairing is never broken and no verdict is fabricated for a failed call; any failure makes the run exit non-zero.

## Evaluation metrics

Let $N$ be the number of scored claims, $\hat{v}_i$ the system verdict and $v_i$ the gold label for claim $i$, $U = \{i : v_i \neq \textit{Supported}\}$ the claims that should be flagged, and $P = \{i : \hat{v}_i = \textit{Supported}\}$ the claims the system affirmed.

| Metric | Definition | Justification |
|:--|:--|:--|
| Verification accuracy | $\frac{1}{N}\sum_i \mathbb{1}[\hat{v}_i = v_i]$ | Aggregate correctness; necessary for comparability |
| Hallucination-catch rate | $\frac{1}{\lvert U \rvert}\sum_{i \in U} \mathbb{1}[\hat{v}_i \neq \textit{Supported}]$ | Recall on claims that should not be affirmed; the harm being prevented |
| False-agreement rate | $\frac{1}{\lvert P \rvert}\sum_{i \in P} \mathbb{1}[v_i \neq \textit{Supported}]$ | Share of affirmations that are wrong: how often the system agrees a claim holds when it does not |
| Latency | Wall-clock time of each arm's own verification call, at p50, p95, p99 | Percentiles, because tail latency governs deployability |
| Tokens per query | Mean prompt plus completion tokens per claim | Free-tier cost proxy, independent of provider prices |

Retrieval is shared across arms and excluded from the per-arm latency figure. Four metrics were considered and rejected as headlines. **Macro-F1** obscures the asymmetry that motivates the work: a false *Supported* is the harmful error, and F1 weights it identically to a missed *Contradicted*. **Calibration error** does not apply, because the system does not emit a probability. **Atomic factual precision in the style of FActScore** [39] scores the fraction of generated atomic facts supported by a knowledge source; the benchmark claims are already atomic and gold-labelled, so claim-level accuracy and catch rate measure the same property without an automated support judge whose own error would enter the metric. **Human rating of verdict quality** was not affordable within the project and would have introduced a rater-agreement problem of its own; its absence is a stated limitation.

## Validation strategy

Internal validation rests on pairing: every arm judges the same claims with the same evidence and model, so gaps are tested on paired per-claim predictions rather than on summary numbers. Accuracy is tested with an **exact McNemar test** [35] on discordant pairs. Catch-rate and false-agreement deltas receive **percentile-bootstrap CIs** from 10,000 resamples with a fixed seed, with items resampled with their pairing intact. External validation comes from replication across two domains and, exploratorily, across base-model scale. A third validation is mechanical: the constraint of Section 3 is re-checked directly against run traces by an independent script (Section 9.7), a check whose result does not depend on sample size.

## Reproducibility

All code is public under the MIT licence, with continuous integration running lint, type checking, and tests on every change. One command re-runs the benchmark (`make phase3-bench CLAIMS=...`), and the offline error analysis (`make error-analysis`) runs from committed traces without a model or database. The sampling seed, sample size, model identifier, corpus coverage, and run date are written into the caption generated with every results table. Every run writes a trace of inputs, retrieved evidence, verdicts, spans, token counts, and timings for the grounded arm. The guarantee audit and Fig. 3 are regenerated by committed scripts (`backend/scripts/`). The residual barrier is provider-side: free-tier endpoints are versioned by the provider and may be withdrawn, so exact numeric replication on a preview model is not guaranteed indefinitely.

## Ethical considerations

No human subjects were recruited and no personal data was collected, so ethics-board review was not required. Both benchmarks are public research datasets used under their published terms: SciFact's claims and annotations under CC BY 4.0 and its abstracts under ODC-By 1.0; FEVER's annotations under the Wikipedia licence terms or, where these are unavailable, CC BY-SA 3.0. The system verifies whether a claim is supported by the literature and never provides medical advice, diagnosis, treatment, or dosing; that boundary is enforced by an intake scope classifier, a non-mutating guardrail disclaimer in every response, and prominent notice in the interface. Uploaded files are processed in memory and never stored. The honest dual-use risk is misplaced trust: a *Supported* verdict certifies that a quotation exists, not that the source is true or that the inference from it is sound (Section 10).

# Proposed System and Approach

## Step-by-step description

A verification request proceeds as follows. (1) The intake guard scans the query for injection patterns and classifies its scope; out-of-scope or adversarial input is refused with a reason. (2) If the caller supplied no evidence, the Retriever runs the semantic and lexical branches, fuses them by RRF, and returns the top 8 chunks with their source identifiers. (3) The Generator produces a candidate answer and decomposes it into atomic claims small enough for one span to settle. (4) For each claim the Verifier applies the span discipline and returns a verdict with a quoted span. (5) The verdict object is validated for shape and passed through `grounded_against`, which normalises span and evidence and tests containment; failure rewrites the verdict to *Unverifiable*, drops the span, and records the downgrade. (6) The Aggregator assembles surviving verdicts into an answer with an evidence-derived confidence signal and an explicit list of disagreements. (7) The Guardrail appends its advisory without modifying any verdict. Step 5 is unconditional and executed outside the model.

## Novelty claim

> **What existing approaches do.** Multi-agent verification systems mediate agreement through *soft* signals: a moderator that weighs argumentative strength [27], a calibrated confidence score [28], or an NLI or token-overlap citation score [29]. Mechanically checked quotation exists, but within single-model classification, with no multi-agent structure, aggregator, or deployed baseline [26]. Hard gates outside natural-language quotation --- formal-proof checking [30], constraint-satisfaction consistency [31] --- do not apply to evidence spans.
>
> **What this approach does differently.** Aletheia makes a *mechanical verbatim-substring match, executed in pipeline code rather than judged by a model*, the precondition for the Verifier's affirmative or contradictory verdict, before that verdict can reach aggregation. A verdict may affirm or contradict a claim only by quoting a span the system can find in the evidence.
>
> **Why this difference matters.** A soft check yields a probability that an assertion is grounded; a hard check yields a guarantee about quotation. A claim cannot be affirmed on evidence the system cannot locate, so the failure mode becomes abstention rather than fabrication, and the property is auditable by a third party from traces alone, without rerunning any model (Section 9.7).

## Theoretical justification

If agents exchange opinions, their agreement is evidence of correlation between the agents, not of correspondence with a source; correlated pretraining makes such agreement cheap to obtain and uninformative once obtained. Requiring each assertion to carry a span that exists in the evidence changes what agreement *is*: a Generator's claim is affirmed only if the Verifier independently locates text in the corpus that states it. The gate is therefore not a better classifier but a change in the admissibility condition for an assertion.

The narrowing is the cost side of the trade. A model that reasons correctly across two sentences, or that knows the answer without being able to isolate one continuous passage, is forced to abstain. Section 9 shows that this cost is small when the base model is weak, and suggests that it grows as the base model becomes strong enough to be right without help --- the boundary condition the gap statement asked for.

# Experimental Setup

| Item | Details |
|:--|:--|
| Hardware | Model inference is remote (provider API) in all arms. Corpus embedding and ingestion run once on a commodity CPU with no GPU, via a local ONNX model; the deployed service runs on a free-tier container |
| Software | Python 3.12+; FastAPI; LangGraph 1.2+; SQLAlchemy 2.0 (async) with Alembic; PostgreSQL with pgvector; fastembed (ONNX); Next.js (TypeScript) frontend |
| Datasets | SciFact `dev` claims over a 5,183-abstract corpus (15,411 chunks); FEVER claims over a seeded Wikipedia slice of approximately 5,000 documents |
| Sampling | Seeded, gold-label-stratified sampling without replacement; n = 100 for headline runs, n = 19--30 for the exploratory sweep; coverage 100.0 percent SciFact, 99.0 percent FEVER |
| Arms | (i) single-LLM baseline; (ii) ungrounded ablation (Verifier role, no span discipline, no gate); (iii) Aletheia grounded. Same model, evidence, corpus, and temperature for all three |
| Models | Google `gemini-3.1-flash-lite-preview` (deployed primary); Groq `llama-3.1-8b-instant` (8B); Groq `llama-3.3-70b-versatile` (70B); OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free` (Nemotron-3-Ultra, 550B total parameters) |
| Hyperparameters | Temperature 0.0; retrieval pool 20 per branch; fused top-$k$ 8; RRF $k$ = 60; chunks of 1,000 characters with 150-character overlap; embedding dimension 384. All fixed, not searched |
| Metrics | Accuracy; catch rate; false agreement; latency p50/p95/p99; tokens per query (Section 6.10) |
| Statistics | One seeded run per configuration (seed 7; seed 13 for the held-out A/B). Exact McNemar for accuracy; percentile bootstrap, 10,000 resamples, seed 7, for catch-rate and false-agreement deltas |

# Results

All numbers are produced by the seeded harness and are traceable to committed run traces and the project's evaluation record. Reporting order is baseline, ungrounded ablation, grounded. The best value in each column is in bold; for false agreement, lower is better.

## Headline benchmark on the deployed model

*Table 1. SciFact `dev`; n = 100 (42 Supported, 21 Contradicted, 37 NEI); seed 7; Google `gemini-3.1-flash-lite-preview`; coverage 100.0 percent; grounded arm V4; run of 3 August 2026.*

| System | Accuracy | Catch rate | False agreement | Latency p50/p95/p99 (s) | Tokens/query |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 79.0% | 93.1% | 10.5% | **1.15** / 2.89 / 6.55 | **1291.8** |
| Multi-agent, ungrounded (ablation) | **80.0%** | 94.8% | 8.1% | 1.37 / **2.62** / **3.11** | 1364.0 |
| Aletheia (grounded) | 79.0% | **96.6%** | **6.1%** | 1.52 / 3.32 / 5.11 | 1676.8 |

*Grounded versus baseline (H1): accuracy exact McNemar p = 1.000 on 6 discordant pairs; catch-rate delta +3.4 points, CI [+0.0, +8.9]; false-agreement delta -4.5 points, CI [-12.3, +0.9]. Grounded versus ablation (H2): accuracy p = 1.000 on 5 discordant pairs; catch-rate delta +1.7 points, CI [+0.0, +5.7]; false-agreement delta -2.0 points, CI [-8.1, +1.3].*

On the deployed model the grounded arm's accuracy is exactly tied with the baseline. Catch rate and false agreement both move in the hypothesised direction and order the three arms as predicted, but both intervals touch or cross zero, so neither H1 nor H2 is confirmed statistically in this configuration. The grounded arm consumes 385.0 more tokens per query than the baseline (about 30 percent) at a higher median latency, which is the H3 measurement. An earlier exploratory run of the same model on the same 100 claims through a different access path (the Kaggle Benchmarks model proxy) also tied, at 80.0 versus 80.0 percent.

![Headline benchmark on the deployed model (SciFact, n = 100, seed 7, `gemini-3.1-flash-lite-preview`, grounded arm V4). The grounded arm leads on both reliability metrics while tying the baseline on accuracy; neither lead is statistically significant. Values are percentages; for false agreement, lower is better.](figures/fig2-headline.pdf){width=100%}

## Weaker-model comparison

The 8B model was run twice on the identical seeded sample, before and after the span-sufficiency revision. Its baseline and ablation arms reproduced exactly, so the difference between the two grounded rows is the effect of the revision.

*Table 2. SciFact `dev`; n = 100; seed 7; Groq `llama-3.1-8b-instant`; coverage 100.0 percent; grounded arm V2; run of 19 July 2026.*

| System | Accuracy | Catch rate | False agreement | Latency p50/p95/p99 (s) | Tokens/query |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 60.0% | 60.3% | 37.7% | **0.30** / 8.93 / 12.95 | **1388.0** |
| Multi-agent, ungrounded (ablation) | 65.0% | 65.5% | 35.7% | 14.06 / 19.00 / 21.66 | 1473.2 |
| Aletheia (grounded) | **69.0%** | **82.8%** | **23.8%** | 0.41 / **0.57** / **1.11** | 1675.6 |

*Grounded versus baseline (H1): accuracy +9.0 points, exact McNemar p = 0.163 on 33 discordant pairs; catch-rate delta +22.4 points, CI [+12.1, +33.3]; false-agreement delta -13.9 points, CI [-23.9, -5.0]. Grounded versus ablation (H2): accuracy p = 0.523 on 22 discordant pairs; catch-rate delta +17.2 points, CI [+8.1, +27.6]; false-agreement delta -11.9 points, CI [-21.3, -3.8].*

*Table 3. The same 8B comparison under the original grounded arm (V1, run of 3 July 2026; same claims, seed, model, and coverage).*

| System | Accuracy | Catch rate | False agreement |
|:--|--:|--:|--:|
| Single-LLM baseline | **60.0%** | 60.3% | 37.7% |
| Multi-agent, ungrounded (ablation) | 65.0% | 65.5% | 35.7% |
| Aletheia (grounded, V1) | 58.0% | **70.7%** | **35.4%** |

*V1 grounded versus baseline: accuracy p = 0.839 on 24 discordant pairs; catch-rate delta +10.3 points, CI [+3.3, +18.6]; false-agreement delta -2.3 points, CI [-9.1, +3.9]. Grounded versus ablation: catch-rate delta +5.2 points, CI [+0.0, +11.7]; false-agreement delta -0.3 points, CI [-5.7, +4.7].*

Under V2 the 8B results support **H1**, with a catch-rate interval excluding zero, and **H2**, with the grounded-versus-ablation false-agreement interval also excluding zero. Accuracy improves by 9 points over the baseline, though that paired comparison is not itself significant. Under V1 the same model and claims showed a significant catch-rate gain but no accuracy gain (58.0 versus 60.0 percent) and no significant false-agreement effect. These two 8B accuracies are the same experiment under two grounded-arm versions, and they are reported together so that neither is read without the other.

The latency columns are not a property of the arms. In the V1 run all three arms had medians between 14.5 and 15.5 seconds; in the V2 run the identical baseline prompt had a median of 0.30 seconds while the ablation's was 14.06 seconds. Because the baseline prompt did not change between the runs, these swings reflect provider-side conditions on a shared free tier. The grounded arm's low V2 latency is therefore not evidence that the gate speeds verification: it used 202.4 more tokens per query than the ablation.

## Error decomposition

Every scored claim in the three n = 100 SciFact runs was classified offline from committed traces.

*Table 4. Outcomes of the grounded arm by cause. Abstention is out of the 63 answerable claims; false grounding is out of the 37 NEI claims.*

| Outcome | 8B, V1 (3 Jul) | 8B, V2 (19 Jul) | Deployed model, V4 (3 Aug) |
|:--|--:|--:|--:|
| Correct | 58 | 69 | **79** |
| Retrieval miss | **0** | 1 | 1 |
| Verifier abstention (evidence present, no span quoted) | 11/63 | 14/63 | **9/63** |
| Wrong direction | 10 | 6 | **4** |
| False grounding (gold NEI, verdict asserts) | 21/37 | 10/37 | **7/37** |

Retrieval is not the bottleneck: at most one of 100 gold passages was missed in any run, so the errors are verifier decisions. At 8B the V2 revision roughly halved false grounding (21/37 to 10/37) and cut wrong-direction errors, at the price of three more abstentions --- the source of its accuracy gain. The deployed model needs the strict single-span discipline less often on both sides, yet this does not convert into an accuracy advantage over the baseline, because the baseline is itself strong enough to answer most claims correctly. That is the mechanism behind the tie in Table 1.

*Caveat.* SciFact's NEI label is defined against its own annotated evidence set, while the system retrieves from the full corpus, so a verdict counted as false grounding sometimes has genuine but uncited support. All false-grounding figures are therefore **upper bounds** on verifier error; separating them requires manual adjudication (Section 13).

## Cross-model robustness (exploratory)

*Table 5. Grounded arm V1 versus the single-LLM baseline by base model; SciFact `dev`; seed 7; coverage 100 percent; runs of 11 July 2026. Every delta is statistically insignificant at these sample sizes and is reported for direction only. The 8B and 70B rows share one sample of 30; the 550B row and its 8B comparator share one sample of 19 (one item excluded in both arms by a provider error).*

| Base model | n | Baseline accuracy | Grounded accuracy | $\Delta$ accuracy | $\Delta$ catch | $\Delta$ false agree |
|:--|--:|--:|--:|--:|--:|--:|
| 8B | 30 | 56.7% | 66.7% | **+10.0** | +17.6 | -11.9 |
| 70B | 30 | 80.0% | 70.0% | -10.0 | +5.9 | -6.0 |
| 8B | 19 | 63.2% | 68.4% | +5.2 | **+30.0** | **-15.7** |
| 550B (Nemotron-3-Ultra) | 19 | **89.5%** | **73.7%** | -15.8 | +0.0 | +0.0 |

Wherever the baseline leaves room, the grounded arm catches more and agrees wrongly less; at 550B the baseline already records 100 percent catch rate and 0 percent false agreement in this sample, so the grounded arm can only tie it. The accuracy delta changes sign with base-model strength in this V1 sweep: positive at 8B, negative at 70B and 550B. The powered comparisons that follow are consistent with that direction --- +9.0 points at 8B under V2 (Table 2) and 0.0 points on the deployed model under V4 (Table 1) --- but they use later grounded-arm versions and cannot confirm the sweep's negative end.

## Absolute performance across scale

Read in absolute terms rather than as deltas, the V1 sweep suggested that the grounded arm improves with the model beneath it. The V2 re-runs on the same seeded samples do not reproduce that pattern.

*Table 6. Grounded arm only, by version and base model; SciFact `dev`; seed 7; coverage 100 percent. False grounding is out of NEI claims and abstention out of answerable claims in each sample.*

| Version | Base model | n | Accuracy | False grounding | Abstention | Retrieval misses |
|:--|:--|--:|--:|--:|--:|--:|
| V1 | 8B | 30 | 66.7% | 6/11 | 2/19 | 0 |
| V1 | 70B | 30 | 70.0% | 4/11 | 5/19 | 0 |
| V1 | 550B | 19 | 73.7% | 1/6 | 4/13 | 0 |
| V2 | 8B | 29 | 72.4% | 4/10 | 2/19 | 0 |
| V2 | 70B | 30 | 66.7% | 2/11 | 7/19 | 1 |
| V2 | 550B | 20 | 70.0% | 2/7 | 4/13 | 0 |
| V4 | Deployed model | 100 | 79.0% | 7/37 | 9/63 | 1 |

Under V1, grounded accuracy rises from 66.7 to 70.0 to 73.7 percent across 8B, 70B, and 550B, and false grounding falls from 6/11 to 4/11 to 1/6. Under V2, on the same claims, accuracy runs 72.4, 66.7, and 70.0 percent, and false grounding 4/10, 2/11, and 2/7: neither is monotone. At these sample sizes a difference of one or two claims moves a row by several points, so the V1 trend is best read as an observation that did not survive the verifier revision, not as a scaling law. Two facts hold in both versions. First, the baseline outscores the grounded arm on accuracy at 70B and 550B (Table 5 and Section 9.6). Second, the grounded arm reached 100 percent catch rate and 0 percent false agreement at 550B in both versions and at 70B under V2 --- but the 550B baseline reached the same ceiling on its sample, so the ceiling at 550B is not a gate effect.

![Grounded-arm behaviour across base-model scale on the same seed-7 SciFact samples, by grounded-arm version. (a) Accuracy rises with scale under V1 but not under V2, and the single-LLM baseline overtakes the grounded arm from 70B. (b) False grounding falls with scale under V1 but not under V2. Denominators are the NEI claims in each sample (n = 30, 30, and 19--20 claims).](figures/fig3-scale.pdf){width=100%}

## A targeted verifier improvement and its limits

The span-sufficiency test (V2) was introduced as an additive change to the grounded prompt and evaluated on a held-out sample against an unchanged control.

*Table 7. Grounded arm, V1 versus V2; SciFact `dev`; coverage 100 percent; runs of 11--17 July 2026. Baselines in parentheses.*

| Base model and sample | n | Accuracy | Catch rate | False agreement |
|:--|--:|:--|:--|:--|
| 8B, seed 13, held out (63.3%) | 30 | 53.3% $\to$ **66.7%** | 76.5% $\to$ 76.5% | 28.6% $\to$ **26.7%** |
| 8B, seed 7 | 30 $\to$ 29 | 66.7% $\to$ **72.4%** | 82.4% $\to$ 81.2% | 21.4% $\to$ 21.4% |
| 70B, seed 7 (80.0%) | 30 | 70.0% $\to$ 66.7% | 94.1% $\to$ **100.0%** | 8.3% $\to$ **0.0%** |
| 550B, seed 7 (89.5% $\to$ 75.0%) | 19 $\to$ 20 | 73.7% $\to$ 70.0% | 100.0% $\to$ 100.0% | 0.0% $\to$ 0.0% |

On the held-out 8B sample the revision raised grounded accuracy by 13.4 points with catch rate unchanged; its error mix shows false grounding falling from 8 to 6 and abstention from 4 to 2. None of these n = 30 differences is significant, and the 8B n = 100 re-run (Table 2) is the powered test of the same change. At 70B the revision halved false grounding (4/11 to 2/11) but raised abstention (5/19 to 7/19), so accuracy slipped while catch rate reached 100 percent and false agreement 0 percent; the 70B baseline reproduced exactly, so this is a clean comparison. The 550B comparison is not: one item was lost to a provider error in the V1 run and the baseline itself moved from 89.5 to 75.0 percent, so its delta is sample drift and is shown only for completeness. The revision therefore **sharpens** the trade-off of Section 9.4 rather than escaping it: the gate can be made more decisive, but decisiveness redistributes error between over-assertion and over-abstention rather than eliminating it.

A later V3 spot-check (8B, seed 7, n = 30, run of 22 July 2026) gave the grounded arm 70.0 percent accuracy against 56.7 percent for the baseline and 70.0 percent for the ablation, with catch-rate delta +23.5 points, CI [+5.6, +45.0], and false-agreement delta -17.9 points, CI [-37.8, -2.7], against the baseline. It is a regression check on an independent small sample, not a headline.

## Second domain: FEVER

*Table 8. FEVER; n = 100 (34 Supported, 33 Refuted, 33 NEI); seed 7; Groq `llama-3.1-8b-instant`; coverage 99.0 percent; grounded arm V4; clean corpus; run of 25 July 2026. Cross-arm latency and token counts were not recorded for this run.*

| System | Accuracy | Catch rate | False agreement |
|:--|--:|--:|--:|
| Single-LLM baseline | 80.0% | 84.8% | 23.8% |
| Multi-agent, ungrounded (ablation) | **85.0%** | **95.5%** | **9.1%** |
| Aletheia (grounded) | 77.0% | 93.9% | 13.8% |

*Grounded versus baseline (H1): accuracy exact McNemar p = 0.648 on 19 discordant pairs; catch-rate delta +9.1 points, CI [+1.5, +17.7]; false-agreement delta -10.0 points, CI [-22.9, +2.0]. Grounded versus ablation (H2): accuracy p = 0.008 on 8 discordant pairs, against the grounded arm; catch-rate delta -1.5 points, CI [-5.0, 0.0]; false-agreement delta +4.7 points, CI [+0.3, +12.6], also against it.*

**The corpus lever.** An earlier run with the same claims and model scored only 56.0 percent accuracy. The only change between the two runs was the corpus: FEVER's Wikipedia text ships in Penn Treebank tokenisation, which an 8B model normalises away while copying an otherwise correct span, after which the containment check rejected a *correct* quote and forced abstention. Folding the markup to plain text at ingestion fixed 24 grounded verdicts and broke 3, moving accuracy from 56.0 to 77.0 percent (+21 points, exact McNemar p = 4.9 $\times$ 10$^{-5}$). This is a before/after re-run of the grounded arm, not a fourth arm. It is a preprocessing effect larger than any architectural effect measured in this study, and a direct warning for anyone gating on pre-tokenised text. The dirty-corpus run recorded 100 percent catch rate and 0 percent false agreement, but that profile was bought by abstaining on nearly every decidable claim; it is not evidence that the guarantee works.

**The cost, reported without softening.** After the fix the grounded arm trails the ablation by 8 points, and the gap is significant against the grounded arm on accuracy and on false agreement: H2 is **not supported** on FEVER. Strict verbatim grounding costs accuracy on paraphrase claims, which is exactly the condition FEVER was chosen to create, while the grounded arm still beats the single-LLM baseline on catch rate with an interval excluding zero.

*Table 9. FEVER grounded-arm verdicts against gold labels (same run as Table 8).*

| Gold $\backslash$ predicted | Supported | Contradicted | Unverifiable |
|:--|--:|--:|--:|
| Supported (34) | 25 | 0 | 9 |
| Refuted (33) | 3 | 21 | 9 |
| NEI (33) | 1 | 1 | 31 |

**The guarantee held exactly.** The 51 asserted verdicts (29 *Supported*, 22 *Contradicted*) were re-checked against their retrieved evidence by an independent script operating only on the committed trace: **51 of 51 carry a span that appears verbatim in the evidence.** Five of the 51 are wrong --- three refuted claims called *Supported*, and two assertions on NEI claims. They are *entailment* errors: the model quoted the evidence faithfully and drew the wrong inference. The remaining 18 misses are abstentions on decidable claims.

The same re-check applied to both SciFact n = 100 traces finds **58 of 58** asserted verdicts verbatim-backed under V2 and **60 of 60** under V4. Because the gate runs on every verdict before a trace is written, this audit does not test the gate's logic; it tests that no asserted verdict reached the record without passing it, and that a third party can confirm this without model access.

![The FEVER run (8B, grounded arm V4). (a) Folding Penn Treebank markup to plain text moved grounded accuracy by 21 points on identical claims with the identical model --- a preprocessing effect larger than any architectural effect measured. (b) The gate's one promise, audited from traces on the domain chosen to break it.](figures/fig4-fever.pdf){width=100%}

## Summary of hypothesis outcomes

*Table 10. Outcomes of the registered hypotheses in the three n = 100 configurations.*

| Hypothesis | SciFact 8B (V2) | SciFact deployed model (V4) | FEVER 8B (V4) |
|:--|:--|:--|:--|
| H1: catch rate versus baseline | **Supported, significant** (+22.4, CI [+12.1, +33.3]) | Direction supported, not significant (+3.4, CI touches 0) | **Supported, significant** (+9.1, CI [+1.5, +17.7]) |
| H2: false agreement versus ablation | **Supported, significant** (-11.9, CI [-21.3, -3.8]) | Direction supported, not significant (-2.0, CI crosses 0) | **Not supported**: ablation better (+4.7 against grounded, CI excludes 0) |
| H3: quantified overhead | +287.6 tokens/query versus baseline; latency not interpretable (Section 9.2) | +385.0 tokens/query (about 30 percent); p50 1.52 s versus 1.15 s | Not recorded across arms |

# Discussion

**What the evidence supports.** Against the single-LLM baseline the safety direction is consistent: catch rate rises and false agreement falls in every n = 100 configuration, and in the exploratory sweep the grounded arm improves on the baseline or ties it at a shared ceiling. H1 is significant where the base model leaves room for correction (8B) and on FEVER, and directional on the deployed model. H2 is weaker and domain-dependent: significant at 8B on SciFact, directional on the deployed model, and reversed on FEVER, where the ungrounded arm beat the gated arm on accuracy and false agreement. The most robust result does not depend on sample size at all: every asserted verdict in every n = 100 run carries a quotation that a third party can find in the evidence.

**The central finding is a boundary condition, not a leaderboard win.** The gate's contribution to accuracy depends on how much error the base model leaves to correct: +9.0 points at 8B (V2, not significant), zero on the deployed model (V4), and, in the under-powered V1 sweep, negative at 70B and 550B. The error decomposition explains the pattern. A strong model already answers most claims correctly, so the span discipline has little error left to correct; what remains for it to do is push the occasional correct answer into abstention, which is pure cost. This reframes the design question from *is structural grounding good* to *when does it pay*. The present data place the crossover somewhere above 8B for these benchmarks, and the harness is built to re-measure it as models change.

**Does the gate pass base-model progress through?** An earlier reading of the V1 sweep suggested that the gated system inherits base-model improvements directly, since its accuracy and false-grounding rate both improved monotonically with scale. The V2 re-runs on the same claims did not reproduce the trend (Table 6), so this paper does not claim it. What survives is weaker but still useful: the gate constrains the *form* of an admissible assertion, not the reading behind it, and nothing in the mechanism caps accuracy below what a strong reader can quote support for. Whether the gated system tracks its base model closely enough to matter is an open question that needs repeated, powered runs at each scale.

**Why FEVER inverted H2.** The ablation beating the gate on paraphrase claims is the predicted consequence of the mechanism, not an anomaly. FEVER claims are crowdworker restatements, so the sentence that entails a claim often shares no single continuous passage with it that the model will commit to, and the gated arm abstains where an ungrounded reader asserts correctly. This suggests that the gate's cost depends on the *lexical distance between claim and evidence*, a property of the domain rather than of the model. That hypothesis is not measured here; Appendix H lists the offline analysis that would test it.

**Two guarantees, kept separate.** Aletheia guarantees *no unsupported assertion*; it does not guarantee *correct entailment*. Five FEVER verdicts quoted the evidence exactly and still reasoned wrongly. This separation was observed for single-model classification by Windisch et al., who found mechanically valid quotes judged semantically supporting in only 48.0 to 78.8 percent of cases [26]; the present results show the same gap inside a multi-agent verification pipeline, and it bounds what any verbatim gate can promise. The gate eliminates fabricated quotation; reading comprehension remains a distinct problem beneath it. The same separation bounds the dual-use risk noted in Section 6.13: a *Supported* verdict certifies that a quotation exists, not that the source is true.

**Relation to prior findings.** The results are consistent with the RAG literature's finding that grounding reduces hallucination [11], [12], [13], and add that the *enforcement mechanism* matters independently of retrieval: the same retrieved evidence yields different reliability depending on whether the span requirement is checked. They also bear on the disagreement between [6], [17], which report that agent interaction helps, and [23], [24], [25], which report correlated agreement. Interaction helps when the exchanged object is checkable. The ablation --- interaction without checkability --- is the condition under which the latter failure mode is expected, although this study's arms do not exchange messages, so the connection is by analogy rather than by direct test (Section 11).

**Unexpected results.** Two were not anticipated. First, latency on the shared free tier varied between runs of the identical baseline prompt by a factor of about fifty (Section 9.2), which makes single-run latency comparisons across arms unreliable in this setting. Second, the FEVER corpus-markup effect: a preprocessing detail accounted for 21 points of accuracy, a caution against attributing to model reasoning what belongs to tokenisation.

**Practical implication.** Where a confidently wrong verdict costs more than an honest abstention --- safety-critical settings, or cost-constrained deployments that must use cheap models --- a hard evidence gate is the appropriate default, and it is most valuable exactly where weak models must be used. For maximum accuracy on strong models with lenient audit requirements, a softer check may dominate; locating that crossover directly is the first item of future work.

# Limitations and Threats to Validity

**Dataset.** Both benchmarks are English and public. SciFact is biomedical and expert-written; FEVER is encyclopedic and crowd-written; neither represents adversarial real-world misinformation. SciFact's NEI label is relative to its own evidence set while the system retrieves from the whole corpus, so every false-grounding figure is an upper bound pending manual adjudication. Headline runs use n = 100 and the scale sweep n = 19--30, the latter too small for inference.

**Methodology.** The most significant omission is a **soft-grounding baseline**. The ablation contrasts a hard gate with *no* check, whereas the comparison closest to the related work --- and the first a reviewer will request --- is a hard gate against an NLI-threshold or alignment-score check [29], [37], [38]. Without it the paper shows that *checking* matters, not that *hardness* matters. Relatedly, the ablation removes the span-discipline prompt block and the mechanical check together, so the H2 effect cannot be apportioned between them. The grounded arm was revised three times during the study (Section 6.7); every comparison is made within a version, but the headline results span V2 and V4. Prompt and retrieval hyperparameters were fixed rather than searched, so no arm is reported at its tuned optimum.

**Construct.** "Multi-agent" describes the deployed Generator--Verifier--Aggregator pipeline. In the benchmark each arm makes one model call per claim, and no arm exchanges messages; the study therefore does not test multi-round debate, and its bearing on debate-specific failure modes [23]--[25] is by analogy. False agreement is operationalised as the false-discovery rate of *Supported* verdicts, one reasonable reading of a failure mode that [23]--[25] define qualitatively.

**Generalisability.** Findings come from two domains and, exploratorily, from four base models across three providers. The located crossover is specific to these benchmarks, prompts, and model families and will move as models change. No supervised leaderboard system (for example MultiVerS [3] on SciFact) was run, so the paper establishes a relative architectural effect, not a state-of-the-art claim.

**Computational.** All work ran on free tiers, which directly limited statistical power: repeats at n = 100 were not affordable, so every reported interval is from a single seeded run and wider than it needs to be. Latency figures come from shared free-tier endpoints and varied by more than an order of magnitude between runs of an unchanged prompt; they are not service-level figures, and cross-arm latency for FEVER was not recorded.

**Evaluation.** No human evaluation of verdict quality, quotation relevance, or the Aggregator's disagreement surfacing was conducted.

**Bias.** Retrieval bias is bounded and measured --- coverage was 100.0 and 99.0 percent, and retrieval accounted for at most one error in 100 --- but the corpus reflects each benchmark's source selection. Provider-side model bias is not separable from the results.

**Reproducibility.** Code, seeds, configuration, and traces are public, and the offline analyses re-run without a model. The deployed model is a *preview* endpoint that the provider may deprecate, so exact replication of Table 1 is time-limited even though the 8B and FEVER runs use a generally available model.

**Threats to validity.** *Internal:* pairing, a shared corpus, a fixed temperature, and control arms that reproduced exactly across runs rule out most confounds; the residual threat is provider-side non-determinism at temperature 0. *External:* two domains support the direction of the effects, not their magnitude in an unseen domain. *Construct:* see above. *Conclusion:* n = 100 with a single run yields intervals wide enough that several directionally supportive results are correctly reported as non-significant, and this paper reports them as such.

# Conclusion

Multi-agent LLM verification can fail by agreeing confidently on a wrong verdict, and prompt-enforced grounding reduces but cannot prevent unsupported assertion. This paper asked whether making a mechanical verbatim-substring match the precondition for an affirmative or contradictory verdict changes that, and at what cost.

Aletheia, a deployed LangGraph pipeline whose Verifier is rewritten to *Unverifiable* by pipeline code whenever it cannot produce an exact evidence substring, was evaluated against a single-LLM baseline and an otherwise identical ungrounded arm on SciFact and FEVER, with one frozen corpus, seeded stratified sampling, and paired significance testing.

Against the baseline, catch rate rose and false agreement fell in every powered configuration, significantly for the 8B model (+22.4 points catch rate) and on FEVER (+9.1 points). On the deployed model the gate tied the baseline on accuracy and led on both reliability metrics without statistical significance. On FEVER's paraphrased claims the ungrounded arm was significantly more accurate. The gate's one promise was kept exactly --- every asserted verdict in every n = 100 run was verbatim-backed, 51 of 51 on the domain chosen to break it --- and its residual errors were failures of entailment, not fabrications.

**Contributions.**

- *(Artifact)* A deployed, free-tier verification service and a seeded, reproducible harness reporting catch rate, false agreement, latency, and token cost against a single-LLM baseline, with committed per-claim traces.
- *(Methodological)* A hard verbatim-evidence gate as the precondition for a Verifier's verdict within a multi-agent pipeline, with the ablation that removes it.
- *(Empirical)* A boundary condition: the gate's accuracy contribution is positive for a weak model, zero for the deployed model, negative on paraphrase-heavy claims, and, in an exploratory sweep, negative for strong models, while its catch-rate advantage holds in direction throughout.
- *(Conceptual)* The separation of *no unsupported assertion* from *correct entailment*, shown inside multi-agent verification by a concrete error class.

Structural reliability mechanisms should be evaluated as trade-offs with a locatable crossover rather than adopted as universal goods, and reporting where such a mechanism costs more than it returns is as much a part of the contribution as reporting where it wins.

# Future Work

**Add a soft-grounding arm** --- motivated by the methodological limitation in Section 11 that the ablation contrasts a hard gate only with no check. An arm that accepts the Verifier's span when an NLI or alignment scorer [37], [38] clears a threshold, rather than on exact containment, evaluated on the same claims in both domains, would isolate hardness from checking and locate the crossover argued for in Section 10.

**Adjudicate the false-grounding class manually** --- motivated by the dataset limitation in Section 11 and the caveat in Section 9.3 that SciFact's evidence-set-relative NEI label makes those counts upper bounds. Adjudicating the 17 flagged items in the two current SciFact headline runs (10 at 8B, 7 on the deployed model) would convert an upper bound into a measurement.

**Run the clean-corpus FEVER comparison at 70B** --- motivated by the generalisability limitation in Section 11 that FEVER was run at one model scale. A partial 70B run was aborted by the free-tier token cap after 29 of 100 items; a complete three-arm run on the clean corpus would show whether a stronger reader closes the 8-point gap to the ablation.

**Run three repeats at n = 100** --- motivated by the computational limitation in Section 11. The harness already aggregates repeats; three repeats per arm on the deployed model would narrow the Table 1 intervals and may resolve its directional but non-significant results.

**Evaluate the live corroborated-fallback path** --- motivated by the scope exclusion in Section 3. The deployed product answers out-of-corpus claims from two independent live sources, which no reported number covers; applying the same harness to that path would show whether the guarantee and its costs carry over to evidence the system did not curate.

# References

[1] J. Thorne, A. Vlachos, C. Christodoulopoulos, and A. Mittal, "FEVER: a large-scale dataset for fact extraction and VERification," in *Proc. NAACL-HLT*, 2018, pp. 809--819. **[V]**

[2] D. Wadden, S. Lin, K. Lo, L. L. Wang, M. van Zuylen, A. Cohan, and H. Hajishirzi, "Fact or fiction: Verifying scientific claims," in *Proc. EMNLP*, 2020, pp. 7534--7550. **[V]**

[3] D. Wadden, K. Lo, B. Kuehl, A. Cohan, I. Beltagy, L. L. Wang, and H. Hajishirzi, "MultiVerS: Improving scientific claim verification with weak supervision and full-document context," in *Findings of NAACL*, 2022. **[V]**

[4] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-resource black-box hallucination detection for generative large language models," in *Proc. EMNLP*, 2023. **[V]**

[5] S. Dhuliawala, M. Komeili, J. Xu, R. Raileanu, X. Li, A. Celikyilmaz, and J. Weston, "Chain-of-Verification reduces hallucination in large language models," in *Findings of ACL*, 2024. **[V]**

[6] Y. Du, S. Li, A. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving factuality and reasoning in language models through multiagent debate," in *Proc. ICML*, 2024. **[V]**

[7] Y. Wang et al., "OpenFactCheck: A unified framework for factuality evaluation of LLMs," in *Proc. EMNLP (System Demonstrations)*, 2024. **[V]**

[8] Y. Yanagita et al., "Accuracy of ChatGPT on the Japanese National Medical Licensing Examination," *JMIR Formative Research*, 2023. **[V]**

[9] R. Massenon et al., "User-reported large language model hallucinations in AI mobile-app reviews," *Scientific Reports*, 2025. **[V]**

[10] E. Asgari, N. Montaña-Brown, M. Dubois, S. Khalil, J. Balloch, J. Au Yeung, and D. Pimenta, "A framework to assess clinical safety and hallucination rates of LLMs for medical text summarisation," *npj Digital Medicine*, vol. 8, no. 1, art. 274, 2025, doi: 10.1038/s41746-025-01670-7. **[V]**

[11] Y. H. Ke, L. Jin, K. Elangovan, H. R. Abdullah, N. Liu, A. T. H. Sia, C. R. Soh, J. Y. M. Tung, J. C. L. Ong, C.-F. Kuo, S.-C. Wu, V. P. Kovacheva, and D. S. W. Ting, "Retrieval augmented generation for 10 large language models and its generalizability in assessing medical fitness," *npj Digital Medicine*, vol. 8, no. 1, art. 187, 2025, doi: 10.1038/s41746-025-01519-z. **[V]**

[12] S. Das, Y. Ge, Y. Guo, S. Rajwal, J. Hairston, J. Powell, et al., "Two-layer retrieval-augmented generation framework for low-resource medical question answering using Reddit data: Proof-of-concept study," *Journal of Medical Internet Research*, vol. 27, p. e66220, 2025, doi: 10.2196/66220. **[V]**

[13] S. Harris, V. T. Ta, M. Trovati, G. Nakhla, F. Latif, and I. Korkontzelos, "Multimodal misinformation detection across diverse languages using RAG and LLMs," *Journal of Intelligent Information Systems*, vol. 64, no. 4, pp. 1719--1746, 2026, doi: 10.1007/s10844-026-01042-x. **[V]**

[14] A. Martín, J. Huertas-Tato, Á. Huertas-García, G. Villar-Rodríguez, and D. Camacho, "FacTeR-Check: Semi-automated fact-checking through semantic similarity and natural language inference," *Knowledge-Based Systems*, vol. 251, art. 109265, 2022, doi: 10.1016/j.knosys.2022.109265. **[V]**

[15] P. N. Ahmad, A. M. Shah, K. Lee, and W. Muhammad, "Misinformation detection on online social networks using pretrained language models," *Information Processing & Management*, vol. 63, no. 1, art. 104342, 2026, doi: 10.1016/j.ipm.2025.104342. **[V]**

[16] Z. Luo, Q. Xie, and S. Ananiadou, "Factual consistency evaluation of summarization in the Era of large language models," *Expert Systems with Applications*, vol. 254, art. 124456, 2024, doi: 10.1016/j.eswa.2024.124456. **[V]**

[17] J. Shi, J. Zhao, X. Wu, R. Xu, Y.-H. Jiang, and L. He, "Mitigating reasoning hallucination through Multi-agent Collaborative Filtering," *Expert Systems with Applications*, vol. 263, art. 125723, 2025, doi: 10.1016/j.eswa.2024.125723. **[V]**

[18] S. Khatri, A. Sengul, J. Moon, and C. A. Jackevicius, "Accuracy and reproducibility of ChatGPT responses to real-world drug information questions," *JACCP: Journal of the American College of Clinical Pharmacy*, vol. 8, no. 6, pp. 432--438, 2025, doi: 10.1002/jac5.70038. **[V]**

[19] M. Omar, S. Nassar, K. Hijazi, B. S. Glicksberg, G. N. Nadkarni, and E. Klang, "Generating credible referenced medical research: A comparative study of openAI's GPT-4 and Google's gemini," *Computers in Biology and Medicine*, vol. 185, art. 109545, 2025, doi: 10.1016/j.compbiomed.2024.109545. **[V]**

[20] N. Kolluri, Y. Liu, and D. Murthy, "COVID-19 misinformation detection: Machine-learned solutions to the infodemic," *JMIR Infodemiology*, vol. 2, no. 2, art. e38756, 2022, doi: 10.2196/38756. **[V]**

[21] Y. Lu and N. Yao, "A fake news detection model using the integration of multimodal attention mechanism and residual convolutional network," *Scientific Reports*, vol. 15, no. 1, art. 20544, 2025, doi: 10.1038/s41598-025-05702-w. **[V]**

[22] C. Kumar, M. Bansal, M. A. Khan, V. Kaushik, M. Arquam, and A. Alabdultif, "Graph-augmented transformer ensemble framework for robust and scalable fake news detection in social media ecosystems," *Scientific Reports*, vol. 16, no. 1, art. 2001, 2025, doi: 10.1038/s41598-025-31653-3. **[V]**

[23] A. Wynn, H. Satija, and G. Hadfield, "Talk isn't always cheap: Understanding failure modes in multi-agent debate," arXiv:2509.05396 [cs.CL], 2025. **[V]**

[24] B. Yao, C. Shang, W. Du, J. He, R. Lian, Y. Zhang, H. Su, S. Swamy, and Y. Qi, "Peacemaker or troublemaker: How sycophancy shapes multi-agent debate," arXiv:2509.23055 [cs.CL], 2025. **[V]**

[25] H. Wan, J. Wu, M. Luo, F. Li, N. Wang, N. F. Chen, and M.-Y. Kan, "The deliberative illusion: Diagnosing factual attrition and stance homogenization in multi-agent LLM deliberation," arXiv:2606.03032 [cs.CL], 2026. **[V]**

[26] P. Windisch, J. Weyrich, F. Dennstädt, D. R. Zwahlen, R. Förster, and C. Schröder, "Show your work: Verbatim evidence requirements and automated assessment of large language models for biomedical text processing of trial eligibility criteria," *Cureus*, 2026, doi: 10.7759/cureus.108666; preprint: medRxiv, doi: 10.64898/2026.03.03.26346690. **[V]**

[27] H. He, Y. Li, D. Wen, Y. Chen, R. Cheng, D. Chen, and F. C. M. Lau, "Debating truth: Debate-driven claim verification with multiple large language model agents," in *Proc. ACM Web Conf. (WWW)*, 2026; arXiv:2507.19090. **[V]**

[28] G. S. Bulusu Venkata, S. Kakarla, M. O. Mohan, and A. Gaddam, "TRUST Agents: A collaborative multi-agent framework for fake news detection, explainable verification, and logic-aware claim reasoning," arXiv:2604.12184, 2026. **[V]**

[29] H. Qian, Y. Fan, J. Guo, R. Zhang, Q. Chen, D. Yin, and X. Cheng, "VeriCite: Towards reliable citations in retrieval-augmented generation via rigorous verification," arXiv:2510.11394 [cs.IR], 2025. **[V]**

[30] J. Ren, "Evidence-grounded verified agentic reasoning: A path toward eliminating LLM hallucination in empirical inference via tool-attested kernel proofs," arXiv:2607.12650 [cs.LG], 2026. **[V]**

[31] S. Miya, "Eidoku: A neuro-symbolic verification gate for LLM reasoning via structural constraint satisfaction," arXiv:2512.20664 [cs.AI], 2025. **[V]**

[32] S. Jeong, Y. Choi, J. Kim, and B. Jang, "Tool-MAD: A multi-agent debate framework for fact verification with diverse tool augmentation and adaptive retrieval," arXiv:2601.04742 [cs.CL], 2026. **[V]**

[33] S. Xiao, Z. Liu, P. Zhang, N. Muennighoff, D. Lian, and J.-Y. Nie, "C-Pack: Packaged resources to advance general Chinese embedding," in *Proc. ACM SIGIR*, 2024, arXiv:2309.07597. **[V]**

[34] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal rank fusion outperforms Condorcet and individual rank learning methods," in *Proc. ACM SIGIR*, 2009, pp. 758--759. **[V]**

[35] Q. McNemar, "Note on the sampling error of the difference between correlated proportions or percentages," *Psychometrika*, vol. 12, no. 2, pp. 153--157, 1947. **[V]**

[36] T. Gao, H. Yen, J. Yu, and D. Chen, "Enabling large language models to generate text with citations," in *Proc. EMNLP*, 2023, arXiv:2305.14627. **[V]**

[37] O. Honovich, R. Aharoni, J. Herzig, H. Taitelbaum, D. Kukliansy, V. Cohen, T. Scialom, I. Szpektor, A. Hassidim, and Y. Matias, "TRUE: Re-evaluating factual consistency evaluation," in *Proc. NAACL*, 2022, arXiv:2204.04991. **[V]**

[38] Y. Zha, Y. Yang, R. Li, and Z. Hu, "AlignScore: Evaluating factual consistency with a unified alignment function," in *Proc. ACL*, 2023, arXiv:2305.16739. **[V]**

[39] S. Min, K. Krishna, X. Lyu, M. Lewis, W. Yih, P. W. Koh, M. Iyyer, L. Zettlemoyer, and H. Hajishirzi, "FActScore: Fine-grained atomic evaluation of factual precision in long form text generation," in *Proc. EMNLP*, 2023, arXiv:2305.14251. **[V]**


```{=latex}
\appendix
\clearpage
```

# Research Plan and Pre-Flight Validation

## Pre-flight validation report (September 2026 revision)

| # | Check | Result | Note |
|--:|:--|:--|:--|
| 1 | Topic specific enough for a focused paper | **Pass** | One mechanism, one pipeline, two datasets, four base models |
| 2 | Research area and venue compatible | **Pass** | Systems-plus-empirical NLP work; IEEE-style preprint (OSF now, arXiv cs.CL later) |
| 3 | Author level matches depth | **Pass** | Final-year undergraduate capstone with faculty co-author; novelty scoped to "to the authors' knowledge, after a full-text search of the closest candidates" |
| 4 | Completed mode has real results | **Pass** | Every table traced to committed runs dated 3 July to 3 August 2026 |
| 5 | Numbers match the evaluation record | **Pass after revision** | Nine mismatches found and fixed; corrected values traced in Appendix J |
| 6 | Verifier version labelled where versions coexist | **Pass after revision** | Section 6.7 and every table caption |
| 7 | Pipeline order correct in text and figure | **Pass** | Checked against the LangGraph definition |
| 8 | References verified at source | **Pass after revision** | Three titles corrected, one DOI prefix corrected, author lists completed (Appendix E) |

## Research plan summary

**Problem definition.** Multi-agent LLM verification permits agreement that no evidence supports, and prompt-enforced grounding cannot prevent it. The problem is to determine what changes, empirically, when the admissibility condition for an assertion is made mechanical rather than behavioural. **Problem type:** design science with an embedded quantitative experiment.

**Significance.** *Academic:* the literature documents both that agent interaction improves factuality and that it produces correlated error, without a structural variable that separates the two cases. *Practical:* verification systems are being deployed into consequential domains now, and the conditions under which a reliability mechanism is worth its cost are unquantified. *Stakeholders:* practitioners deploying verification under cost constraints, researchers building multi-agent pipelines, auditors who need to check an assertion after the fact, and end users.

**Literature landscape.** Foundational: [1], [2], [3], [4], [6]. Recent: [23]--[29], [11], [17], [7]. Soft-consistency scoring: [36]--[38]. Organised thematically in Section 2.

**Delta from the August draft.** The problem, gap, objectives, hypotheses, and metrics are unchanged. Objective 3 and RQ4 are now labelled exploratory; Contribution 3 no longer claims monotone scaling; Contribution 4 is reframed as an extension of [26] rather than a first; and the metrics section adds atomic factual precision [39] and human rating to the rejected-metric notes.

# Research Gap Statement

No empirical study evaluates a hard, mechanically verified verbatim-evidence gate --- one that permits an affirmative or contradictory verdict only when it quotes a verbatim span of the retrieved evidence, checked in code --- as the structural precondition for verdicts in **multi-agent** claim verification. Mechanically checked quotation has been evaluated for single-model classification [26], and multi-agent claim verification grounds evidence softly, through LLM-judgment moderation, calibrated confidence, or NLI scoring [27]--[29]. Consequently the catch-rate, false-agreement, accuracy, latency, and cost trade-offs of a hard gate inside a multi-agent structure, and how they move with base-model scale and claim domain, are unmeasured. *Evidence base:* the 35-article journal review of Section 2 for the soft-enforcement, single-model, and unreported-cost patterns; conference and preprint sources [26]--[32] for the closest antecedents.

# Contribution Summary

| # | Contribution | Type |
|--:|:--|:--|
| 1 | Aletheia: a deployed, free-tier, publicly runnable verification service whose benchmarked Verifier and gate are the deployed code | Artifact |
| 2 | A seeded, reproducible harness reporting accuracy, catch rate, false agreement, latency percentiles, and tokens per query against a baseline and an isolating ablation, with committed per-claim traces and offline re-scoring | Artifact |
| 3 | A structural evidence gate making a mechanical verbatim-substring match the precondition for a Verifier's verdict in a multi-agent pipeline | Methodological |
| 4 | A boundary condition: the gate's accuracy contribution is positive at 8B, zero at the deployed model, negative on paraphrase claims, and, exploratorily, negative for strong models | Empirical |
| 5 | A preprocessing finding: Penn Treebank markup alone accounted for 21 accuracy points under a verbatim gate | Empirical |
| 6 | An audit showing every asserted verdict in all three n = 100 runs verbatim-backed (51/51, 58/58, 60/60), with residual errors that are entailment failures | Empirical and conceptual |

# Source Registry

**[V] Verified --- all 39 sources.** Journal articles were checked against Crossref records; preprints against their arXiv or medRxiv records; [26], [27], and [28], the closest prior art, were fetched from their records of origin, and [27] and [28] were read in full text in an earlier pass.

**[L] Likely real --- none.** **[U] Could not verify --- none.**

**Sources added in this revision.** [36] ALCE, [37] TRUE, [38] AlignScore, and [39] FActScore, each verified against its arXiv record, with the abstract read, to support the soft-grounding discussion (Sections 2.2, 2.3, 11, 13) and the rejected-metrics note (Section 6.10).

**Sources not cited but examined.** GKMAD (*Expert Systems with Applications*, 2025) and "Debating to Verify" (2025--2026) were confirmed real and abstract-checked during the novelty search; neither describes a hard gate. They are not cited because no claim in the paper depends on them.

**Full bibliographic details** for the 35 reviewed journal articles are in the supplementary literature table (`backend/scripts/literature-review-table.csv`).

# Citation Verification Notes

1. **Three titles were paraphrases despite a [V] tag.** [26], [27], and [28] carried descriptive titles in the August draft. Each now carries the title of record: Windisch et al. [26]; He et al. [27], "Debating truth: Debate-driven claim verification with multiple large language model agents"; and Bulusu Venkata et al. [28], "TRUST Agents: A collaborative multi-agent framework for fake news detection, explainable verification, and logic-aware claim reasoning". The earlier tag meant the works existed, not that every field was right; the tag now means both.
2. **One DOI prefix was stale.** medRxiv issues DOIs under the prefix 10.64898 from 2026, and the draft's 10.1101 form of [26] does not resolve. The peer-reviewed *Cureus* version (doi: 10.7759/cureus.108666) is now cited as primary, with the preprint alongside.
3. **One characterisation was corrected.** The draft described [26] as forcing abstention when a quote fails. Its record states that quotes were mechanically validated as exact substrings after whitespace normalisation and separately judged for semantic support; the text now says exactly that. The same record reports that valid quotes were judged supporting in only 48.0 to 78.8 percent of cases, which led to the reframing of Contribution 4.
4. **Author lists completed** for [20], [21], and [22] from Crossref, via the PubMed Central identifier converter for [20] and [22].
5. **Dataset licences corrected.** The draft stated SciFact as CC BY-NC 2.0, a label taken from a third-party dataset card; the SciFact repository's own licence file states CC BY 4.0 for claims and ODC-By 1.0 for abstracts. FEVER's terms were added from its dataset card.
6. **Preprint identifiers may change on publication.** Entries [23]--[25], [28]--[32] are cited from preprint records and should be reconciled with published versions where these appear.
7. **No DOI, URL, author name, dataset, or statistic was generated to fill a gap.**

# Simulated Peer Review (Reviewer #2)

**Summary.** The paper makes a verbatim-substring check, executed in code, the precondition for a Verifier's affirmative or contradictory verdict; implements it in a deployed pipeline; and compares it with a single-LLM baseline and an ungrounded ablation on SciFact and FEVER. It reports a boundary condition --- the gate helps accuracy for a weak model, is neutral on the deployed model, and hurts on paraphrase claims --- plus a trace audit showing every asserted verdict is quotation-backed.

**Strengths.** (1) The controls are unusually well checked: the baseline and ablation reproduce exactly across runs, so version effects are isolable. (2) Negative results (the FEVER H2 reversal, the deployed-model tie, the failed replication of the scaling trend) are reported with statistics rather than hedged. (3) The trace audit is checkable without model access. (4) The Penn Treebank finding is a genuine methodological warning. (5) Reproducibility is well above the field norm.

**Weaknesses.**

1. **No soft-grounding baseline.** The ablation removes both the prompt block and the check, and there is no NLI-threshold arm. The paper can claim that *checking* matters, not that *hardness* matters --- yet hardness is the title's claim.
2. **Single-run power at n = 100.** The deployed-model results, which the paper leads with, are not significant. Without repeats one cannot tell a tie from a small effect.
3. **Exploratory scale rows.** Rows at n = 19--30 carry much of the "strong models" story. The authors now say so, but the boundary condition's negative end rests on them.
4. **NEI upper bound.** False grounding, the error class the verifier revision targets, is an upper bound whose tightness is unknown; the V1-to-V2 improvement could partly be movement within annotation noise.
5. **Generality.** Two English benchmarks, one of them chosen because it is adversarial. Nothing is shown for a real misinformation stream or another language.
6. **Is this multi-agent?** In the benchmark each arm is one model call per claim, and no agents exchange messages. The multi-agent framing rests on the deployed pipeline, which is not what is measured. The connection to debate failure modes [23]--[25] is analogy, not test.

**Questions for the authors.** (1) Would a practitioner adopt the gate in a paraphrase-heavy domain where the ungrounded arm is better on accuracy *and* false agreement? Is auditability sufficient, and for whom? (2) How much of the 8B gain survives an ablation that keeps the span-discipline prompt but drops the containment check? (3) What would adjudicating the 17 false-grounding items do to Table 4? (4) Why lead with the deployed model rather than the configuration where the hypotheses are supported?

**Minor.** Report per-arm completion tokens so that the latency discussion can be settled. Consider moving Tables 3 and 7 to a supplement.

**Recommendation: Major revision.** The construction is sound, the evaluation discipline is strong, and the honesty about negative results is a credit. The missing soft-grounding arm and the single-run headline leave the central mechanistic claim untested against its nearest alternative.

# Reviewer Vulnerability Report

| Rank | Vulnerability | Likely attack | Current mitigation | Residual exposure |
|--:|:--|:--|:--|:--|
| 1 | No soft-grounding arm | "You showed checking matters, not hardness" | First limitation and first future-work item | **High** until run |
| 2 | "Multi-agent" framing | "Your benchmark is one call per arm" | Section 6.3 and construct-validity limitation state it plainly | **Medium** |
| 3 | Deployed-model headline not significant | "Your significant results use a model nobody deploys" | Boundary condition framed as the contribution; intervals reported | **Medium**; repeats would help |
| 4 | H2 reversed on FEVER | "Your ablation beat your system" | Reported unsoftened; lexical-distance explanation labelled as a hypothesis | **Medium** |
| 5 | Scale rows under-powered and version-mixed | "Your scaling story is noise" | Labelled exploratory; failed replication reported | **Low--medium** |
| 6 | Verifier revised during the study | "You tuned on the test set" | Held-out seed-13 test; versions labelled; comparisons within version | **Low--medium** |
| 7 | False grounding is an upper bound | "Your error decomposition is not a measurement" | Stated at first use and in limitations | **Low** |
| 8 | No leaderboard comparison | "Absolute quality unassessable" | Stated; relative effect claimed only | **Medium** |
| 9 | Contamination | "Both benchmarks predate the models" | Relative-gap reporting | **Low** |

# Improvement Roadmap

Ordered by return on effort before journal submission.

1. **Run three repeats at n = 100 on the deployed model** (Appendix I, item 4). Narrows Table 1's intervals. *Effort: one quota day.*
2. **Add the soft-grounding arm** (Appendix I, item 1). Answers the top vulnerability. *Effort: one implementation session plus one run per domain.*
3. **Adjudicate the 17 false-grounding items** (Appendix I, item 2). *Effort: one focused session, no quota.*
4. **Record per-arm completion tokens** in traces for all arms, so latency and cost can be attributed. *Effort: a harness change.*
5. **Lexical-distance analysis on FEVER**, offline from existing traces: per-claim overlap between claim and evidence against abstention. Tests the explanation offered in Section 10. *Effort: hours; no quota.*
6. **Run MultiVerS on the same SciFact sample** for an absolute reference point. *Effort: one session, subject to compute.*
7. **Full-text pass on GKMAD and "Debating to Verify"** before arXiv submission. *Effort: one reading session.*
8. **Compress to a venue limit** if one applies: move Tables 3, 5, and 7 to a supplement and fold Sections 4--5 into the Introduction.

```{=latex}
\clearpage
```

# Experiment Requirements

Only the experiments listed in Section 13 are included. Quota estimates use the measured tokens per query from Tables 1 and 2 and the free-tier limits recorded in the project's evaluation record (Gemini: 15 requests per minute, 1,000 per day).

| # | Experiment | Metric | Data | Quota estimate |
|--:|:--|:--|:--|:--|
| 1 | Soft-grounding arm | Accuracy, catch rate, false agreement of hard versus soft gate; paired deltas | SciFact and FEVER seed-7 n = 100; threshold set on the seed-13 n = 30 slice | One Verifier call per claim: about 130 calls and about 220k tokens per domain per model; the NLI or alignment scorer runs locally on CPU |
| 2 | Manual NEI adjudication | Adjudicated false grounding versus upper bound | The 17 flagged items (10 at 8B V2, 7 at V4) with their retrieved evidence | No model calls; two annotators recommended, with agreement reported |
| 3 | Clean-corpus FEVER at 70B | Table 8 metrics at 70B | FEVER seed-7 n = 100, clean corpus | About 117k tokens for three arms, above the Groq free-tier daily cap; needs pacing across days or a paid tier |
| 4 | Three repeats at n = 100 | Table 1 metrics as mean $\pm$ SD, narrower CIs | SciFact seed-7 n = 100, deployed model | 900 requests (three arms, three repeats) and about 1.3M tokens; fits within one day's request limit at 15-second pacing |
| 5 | Live corroborated-fallback path | Guarantee audit, catch rate, abstention, latency on out-of-corpus claims | FEVER seed-7 n = 100 with the corpus disabled, using the two-source live fallback | About two Verifier calls per claim (one per source): about 200 calls and 340k tokens, plus free public-API lookups |

**Output table templates.**

*Experiment 1:*

| System | Domain | Accuracy | Catch rate | False agreement | $\Delta$ vs hard gate (CI) |
|:--|:--|--:|--:|--:|:--|
| Hard gate (V4) | SciFact / FEVER | | | | --- |
| Soft gate ($\tau$ = ...) | SciFact / FEVER | | | | |

*Experiment 2:*

| Run | Flagged false grounding | Adjudicated genuine | Adjudicated uncited support | Inter-annotator $\kappa$ |
|:--|--:|--:|--:|--:|
| 8B V2 | 10 | | | |
| Deployed V4 | 7 | | | |

*Experiments 3 and 4 use the layout of Tables 8 and 1 respectively, with mean $\pm$ SD for Experiment 4. Experiment 5:*

| Path | n | Asserted | Verbatim-backed | Catch rate | Abstention | p50 latency (s) |
|:--|--:|--:|--:|--:|--:|--:|
| Live corroborated fallback | | | | | | |

# Quality Assurance Record

## Structural integrity checklist

| # | Check | Result | Note |
|--:|:--|:--|:--|
| 1 | Research problem specific and bounded | Pass | Section 3, with explicit exclusions |
| 2 | Gap supported by cited evidence | Pass | Derived per theme; evidence base stated |
| 3 | Objectives measurable | Pass | Each carries a measurability criterion |
| 4 | RQs match methodology | Pass | Each RQ names its statistic |
| 5 | Methodology reproducible | Pass | Hyperparameters, normalisation, prompts, seeds, versions, and commands stated |
| 6 | Metrics appropriate and justified | Pass | Formulas from the scoring code; four rejected metrics with reasons |
| 7 | Conclusions supported by evidence | Pass | Non-significant results labelled throughout |
| 8 | Unsupported claims | Pass | Monotone-scaling and "prior work conflates" claims removed |
| 9 | Citation and bibliography correspondence | Pass | All 39 entries cited; no orphan citations |
| 10 | References tagged | Pass | [V] on all 39 |
| 11 | Language original | Pass | |
| 12 | Unnecessary repetition | Pass with note | Limitations deliberately restated in Sections 9, 11, and 13 |
| 13 | Logical inconsistencies | Pass | H2 cell corrected to the ablation comparison |
| 14 | Limitations thorough | Pass | Eight categories plus four validity types |
| 15 | Meaningful contribution | Pass | Four typed contributions |
| 16 | Abstract reflects content | Pass | Tie, 8B gain, FEVER cost, guarantee, boundary sentence; under 250 words |
| 17 | Free of exaggeration | Pass | No accuracy win claimed; "suggests" for exploratory results |
| 18 | Acronyms defined on first use | Pass | LLM, RAG, NLI, RRF, NEI, CI |
| 19 | Within target length | Pass | Main body within the 16--20 page target |
| 20 | Avoids generic phrasing | Pass | |
| 21 | Every number matches the evaluation record | Pass | Anti-fabrication audit below |
| 22 | Every table states model, n, seed, coverage | Pass | Captions of Tables 1--10 |
| 23 | Verifier version labelled where versions coexist | Pass | Section 6.7 and captions |
| 24 | Pipeline order correct in text and figure | Pass | Intake (optional), Retriever (optional), Generator, Verifier, gate, Aggregator, Guardrail |
| 25 | No implied accuracy win | Pass | Charter criterion "beats baseline on accuracy" is not met on the deployed model and is not claimed |
| 26 | No AI attribution | Pass | Authors are the two named persons only |

## Anti-fabrication audit

| Claim | Source | Verified |
|:--|:--|:--|
| Table 1 and footnote | Evaluation record §6.2 (run of 3 Aug 2026; trace `scifact_gemini.jsonl`) | Yes |
| Table 2 and H1 footnote | Evaluation record §6.2 historical run (19 Jul 2026) | Yes |
| Table 2 H2 footnote | Harness-generated footnote, evaluation record at commit `c85309c`; restored to §6.2 | Yes |
| Table 3 | Evaluation record at commit `334bfce` (run of 3 Jul 2026) | Yes |
| Table 4 | `make error-analysis` on `scifact-2026-07-03-old-verifier.jsonl`, `scifact_revalidation.jsonl`, `scifact_gemini.jsonl` | Yes, re-run |
| Tables 5 and 7 | Evaluation record §6.4--§6.5 | Yes |
| Table 6 | `make error-analysis` on the seven sweep traces (seed 7, sample sizes as captioned) | Yes, re-run |
| Tables 8 and 9, corpus lever | Evaluation record §6.6 | Yes |
| 51/51, 58/58, 60/60 | Guarantee-audit script over the three traces | Yes, re-run |
| Grounded-arm versions and dates | Git history of the Verifier prompt and gate code | Yes |
| Corpus statistics and coverage | Ingestion record; corpus file checked against all 300 dev claims | Yes |
| Hyperparameters, model identifiers, fold set | Configuration and source code | Yes |
| Dataset licences | SciFact repository licence file; FEVER dataset card | Yes |
| Literature findings [8]--[22] | 35-article review table | Yes |
| [26] finding (48.0--78.8 percent) | medRxiv record abstract | Yes |
| Novelty claim | Search with full-text reads of [27], [28]; record-level read of [26] | Scoped as positioning |

# Alternative Titles

**Primary (used).** A Hard Verbatim-Evidence Gate as the Precondition for Multi-Agent Claim Verification: Design, Deployment, and Empirical Boundary Conditions

**Alternative 1.** When Structural Grounding Pays: A Mechanically Verified Evidence Gate for Multi-Agent Claim Verification

**Alternative 2.** Quote or Abstain: Enforcing Verbatim Evidence as a Structural Constraint on LLM Claim Verification

*Both alternatives are under 20 words and avoid superlatives. Alternative 1 foregrounds the boundary condition; Alternative 2 foregrounds the mechanism and drops "multi-agent", which Reviewer #2 questions.*
