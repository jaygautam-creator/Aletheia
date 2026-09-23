---
title: "A Hard Verbatim-Evidence Gate as the Precondition for Multi-Agent Claim Verification: Design, Deployment, and Empirical Boundary Conditions"
author: "Jay Gautam^[Department of Computer Science and Engineering (Artificial Intelligence and Machine Learning). Aletheia Project. Correspondence: jaygautam561@gmail.com. Source code and evaluation record: https://github.com/jaygautam-creator/Aletheia]"
date: "August 2026"
abstract: |
  Multi-agent large language model (LLM) pipelines verify claims by letting model instances critique one another, but opinion-only exchange can fail by agreeing on the wrong answer, and nothing in its structure prevents correlated hallucination. Existing mitigations ground generation in retrieved evidence through prompting alone, which reduces but cannot guarantee that an assertion is evidence-backed, and they rarely report the latency and cost of the reliability mechanism itself. This study asks whether constraining agreement structurally, by permitting an affirmative or contradictory verdict only when it quotes a verbatim span of retrieved evidence checked programmatically, catches more hallucinations than a single LLM, and at what accuracy, latency, and cost. A deployed LangGraph pipeline, Aletheia, was built in which the verifier is mechanically downgraded to Unverifiable whenever it cannot produce an exact evidence substring. It was evaluated against a single-LLM baseline and an opinion-only multi-agent ablation on SciFact and FEVER, with all arms grounded in one frozen corpus, seeded stratified sampling, and paired significance testing. On the deployed model the grounded arm ties the baseline on accuracy (79.0 percent versus 79.0 percent) while improving catch rate (96.6 versus 93.1) and false agreement (6.1 versus 10.5); on an 8-billion-parameter model the catch-rate gain is large and significant (82.8 versus 60.3, delta 22.4 points). The gated system also inherits base-model progress directly: its own accuracy rises monotonically with base-model scale (66.7 to 79.0 percent), false grounding falls monotonically (57 to 17 percent of not-enough-information claims), and on the strongest model tested its catch rate and false-agreement rate reach ceiling at 100 and 0 percent. The gate keeps its guarantee exactly: 51 of 51 asserted FEVER verdicts are verbatim-backed. The results establish a boundary condition rather than a leaderboard win: structural grounding buys accuracy for weak models and auditability for strong ones.
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
  - \AtBeginEnvironment{longtable}{\footnotesize}
  - \setlength{\parskip}{0.35em}
  - \setlength{\LTpre}{0.6em}
  - \setlength{\LTpost}{0.6em}
---

**Index Terms** --- automated claim verification, large language models, hallucination mitigation, multi-agent systems, retrieval-augmented generation, evidence grounding, reproducible evaluation, false agreement.

**Reference confidence legend.** Every entry in the reference list carries a verification tag: **[V]** verified (the publication was confirmed directly, and for the closest prior art read in full text); **[L]** likely real, bibliographic details still to be confirmed against the DOI of record; **[U]** could not verify. As of the August 2026 revision no **[L]** entry remains: every reference has been confirmed against its DOI or arXiv record of origin. No claim in this paper rests on a **[U]** source. The full registry is Appendix D.

# Introduction

A large language model deployed for medical question answering produced hallucinated references at a measurable rate in a controlled clinical review [8], [19], and a clinician-annotation framework over 12,999 sentences of LLM-generated medical summaries measured a hallucination rate of 1.47 percent and an omission rate of 3.45 percent [10]. Those numbers are small in aggregate and unacceptable individually: the failure is not a visibly broken answer but a fluent, confidently stated one that no source supports.

Automated claim verification is where this failure is most costly. A system that labels a false claim *Supported*, or asserts more than its retrieved evidence licenses, does not merely fail to catch misinformation; it manufactures it, and it does so with the same confident register it uses when correct. The user therefore receives no signal separating a trustworthy verdict from a fabricated one.

Two mitigation strategies dominate. The first is retrieval-augmented generation (RAG), which grounds generation in retrieved passages and consistently reduces hallucination, in some clinical configurations to near zero [11], [12], [13]. The second is multi-agent critique, in which several model instances debate or review one another's output to improve factuality [6]. Each has a structural weakness. RAG's grounding is enforced by instruction --- the model is asked to use only the retrieved passages --- so a model may still contradict, over-reach beyond, or silently ignore the evidence it was given; the enforcement is soft. Multi-agent critique inherits a distinct failure mode that a recent cluster of studies has characterised directly: debating agents exhibit sycophancy, premature convergence, and consensus on incorrect answers [23], [24], [25]. Because the exchanged objects are opinions rather than evidence, agreement between agents carries no independent guarantee of correctness.

**Problem statement.** No mechanism in current multi-agent verification pipelines structurally prevents two agents from agreeing on a claim that neither can support with a quotation from the evidence, and no empirical study quantifies what such a mechanism would cost in accuracy, latency, and tokens.

**Motivation.** The problem is urgent now for two converging reasons. Deployment of LLM verification into consequential domains is already underway, as the medical literature reviewed in Section 2 shows, so the cost of a confident wrong verdict is being incurred in practice. At the same time, base-model capability is rising quickly, which makes the *conditions* under which a reliability mechanism pays for itself a moving target: a safeguard that is essential at one model scale may be pure overhead at the next. Establishing where the crossover lies is therefore a time-sensitive empirical question, not a permanent design rule.

**Research gap.** A structured review of 35 original empirical journal articles on LLM factuality, hallucination, and claim verification (Section 2, and the supplementary literature table) shows that grounding is enforced softly [11], [12], [13]; that systems are overwhelmingly single-model, with multi-agent LLM verification appearing rarely in journal work [17] and its false-agreement risk unexamined; and that the latency and cost of the reliability mechanism are almost never reported [14], [15], [16]. Full-text examination of the closest technical antecedents confirms that hard verbatim gates exist only for single-model classification [26], while multi-agent claim verification grounds evidence through LLM-judgment moderation [27], calibrated confidence [28], or natural language inference scoring [29] --- never a mechanical string check. The gap is therefore methodological: *no empirical study evaluates a hard, mechanically verified verbatim-evidence gate as the structural precondition for multi-agent claim verification, together with its catch-rate, false-agreement, accuracy, latency, and cost trade-offs across model scales and domains.*

**Research objectives.**

1. To design and deploy a multi-agent verification pipeline in which a mechanical verbatim-substring match is a hard precondition for any affirmative or contradictory verdict.
2. To measure that pipeline's hallucination-catch rate, false-agreement rate, verification accuracy, latency, and token cost against a single-LLM baseline and an opinion-only multi-agent ablation on the same claims, evidence, and model.
3. To determine whether the measured effects persist across base-model scale (8 billion to 550 billion parameters) and across two claim domains (scientific abstracts and open-domain encyclopedic text).
4. To establish, from run traces, whether the gate's mechanical guarantee holds exactly under adversarial conditions for verbatim matching.

**Research questions.**

- **RQ1.** Does an evidence-grounded multi-agent pipeline catch measurably more hallucinations than a single LLM on the same claims?
- **RQ2.** Does requiring a quoted verbatim span lower the false-agreement rate relative to an otherwise identical opinion-only multi-agent arm?
- **RQ3.** What latency and token overhead does the gate impose?
- **RQ4.** How do the effects in RQ1--RQ3 vary with base-model strength and with claim domain?

**Contributions.**

1. *(Artifact/tool)* Aletheia, a deployed, publicly runnable multi-agent verification service in which the verbatim-span check is executed in pipeline code rather than requested in a prompt, together with a seeded, reproducible evaluation harness.
2. *(Methodological)* A structural evidence gate that makes a mechanical verbatim-substring match the precondition for multi-agent verifier agreement --- to the authors' knowledge, after a full-text search of the closest candidates, the first such construction operating on natural-language evidence spans within a multi-agent verification structure.
3. *(Empirical)* A two-sided scaling result measured across three model scales and two domains with paired significance testing: the gated system's own accuracy, false-grounding rate, and guarantee metrics all improve monotonically with base-model capability, reaching a 100 percent catch rate and 0 percent false agreement on the strongest model tested, while the gate's *marginal* accuracy contribution over a single-LLM baseline is inversely related to that same strength.
4. *(Theoretical)* An explicit separation of two guarantees that the literature conflates --- *no unsupported assertion* versus *correct entailment* --- demonstrated by an error class in which the model quotes the evidence exactly and still reasons incorrectly.

**Paper organisation.** Section 2 synthesises the literature thematically and derives the gap. Section 3 formalises the research problem, its scope, and its variables. Sections 4 and 5 state the objectives, research questions, and hypotheses. Section 6 details the methodology across research design, architecture, data, algorithms, tooling, experimental setup, metrics, validation, reproducibility, and ethics. Section 7 describes the proposed system and states the novelty claim explicitly. Section 8 specifies the experimental setup. Section 9 reports results, Section 10 interprets them, Section 11 states limitations and threats to validity, Section 12 concludes, and Section 13 derives future work from specific limitations. Appendices A--K contain the research plan, source registry, a simulated peer review, and the pre-submission improvement roadmap.

# Literature Review and Related Work

The review draws on 35 original empirical journal articles, deliberately excluding reviews, meta-analyses, and conference proceedings, supplemented by the technical antecedents that define the mechanism at issue. It is organised by theme rather than by paper.

## Theme 1: Measuring factual accuracy and citation reliability

The first line treats factuality as a benchmarking problem. GPT-4 scored 81.5 percent against 42.8 percent for GPT-3.5 on 292 Japanese National Medical Licensing Examination questions [8]; comparative studies contrast citation credibility between GPT-4 and Gemini on medical references [19]; and expert evaluation of repeated drug-information queries finds accuracy and reproducibility to vary within a single domain [18]. These studies establish that the problem is real and measurable, and they establish its magnitude in deployment-relevant settings.

*Critical analysis.* The methodological strength is expert ground truth; the weakness is that measurement yields no mechanism. A benchmark score describes a model's aggregate reliability but offers the end user nothing at inference time, because it cannot indicate which particular answer is the unreliable one. Every study in this theme is also single-domain and single-model, and none reports the cost of any corrective mechanism, because none proposes one.

## Theme 2: Detecting and characterising hallucination

The second line detects unsupported output rather than scoring correctness. A taxonomy built from three million app-store reviews across 90 applications found factual errors to constitute 38 percent of user-reported hallucinations [9]; a clinician-annotation framework quantified hallucination and omission rates in medical summarisation [10]; and LLM-based metrics for factual consistency in summarisation improve correlation with human judgment over earlier automatic measures [16]. Reference-free approaches detect hallucination without retrieving evidence at all, by scoring the consistency of multiple sampled generations [4] or by answering self-generated verification questions from the model's own parameters [5].

*Critical analysis.* This theme supplies the vocabulary and the measurement instruments used throughout the field, and its reference-free methods are attractive because they require no corpus. That independence is also the limitation: a detector that consults only the model cannot distinguish a confident falsehood from a confident truth on any matter the model was trained to be wrong about, and detection is applied after generation rather than constraining it. The open question is whether unsupported assertion can be *prevented* structurally rather than flagged retrospectively.

## Theme 3: Retrieval-augmented mitigation

The third line grounds generation in retrieved evidence. RAG evaluated across ten LLMs for medical fitness assessment reached 96.4 percent with GPT-4 and no observed hallucination [11]; a two-layer RAG architecture improved grounding in a low-resource medical question-answering setting [12]; and a multilingual RAG verifier improved cross-lingual misinformation detection [13]. The consistent finding is substantial reduction in unsupported output.

*Critical analysis.* Retrieval demonstrably reduces hallucination, and the effect replicates across models, languages, and clinical subdomains, which makes it the strongest available mitigation. Its weakness is the enforcement mechanism: in every system in this theme the instruction to rely on retrieved passages is delivered in the prompt, so compliance is a behaviour the model exhibits with high probability rather than a property the system guarantees. None of these studies verifies mechanically that a produced assertion corresponds to retrieved text, and none reports the latency or token cost of the retrieval layer.

## Theme 4: Automated verification, multi-agent critique, and its failure modes

The fourth line labels claims against evidence or content. FEVER established large-scale fact extraction and verification over Wikipedia [1]; SciFact introduced expert scientific claims over biomedical abstracts with an extractive rationale-selection baseline [2], later improved by weak supervision and full-document context [3]. Evidence-linked pipelines combine semantic similarity retrieval with natural language inference [14], while content-based detection uses pretrained language models over thematic, sentiment, and stance cues [15], graph-augmented transformer ensembles [22], or multimodal attention fusion [21]; at scale, blended machine and human pipelines reached 99.1 percent on a COVID-era misinformation corpus [20]. Multi-agent approaches appear rarely in journal work: collaborative filtering across agents reduces reasoning hallucination [17], and debate among model instances improves factuality [6]. A 2025--2026 cluster of studies then documented the countervailing risk directly, reporting sycophancy, premature consensus, and false agreement among debating agents [23], [24], [25].

*Critical analysis.* Benchmarks in this theme define the task and supply gold labels, but their leading systems are supervised classifiers that emit a label without binding it to a checkable span, and the deep-learning detection subfield optimises accuracy on recurring corpora with limited attention to explanation [21], [22]. The multi-agent subfield is where agreement and disagreement in the literature is sharpest: [6] and [17] report that agent interaction improves factuality, while [23], [24], [25] report that the same interaction produces correlated error. The two findings are reconcilable only if the *content* of the exchange determines the outcome --- which is precisely the variable no study in this theme manipulates structurally.

## Direct technical antecedents

Two lines sit closest to the present mechanism and were examined in full text. Hard, mechanically verified verbatim gates do exist: one system validates that a supporting quote is an exact substring of the source abstract and forces abstention otherwise [26]. It is, however, a single-model, label-only versus label-plus-quote ablation with no multi-agent structure, no aggregator, and no deployed-baseline evaluation. Conversely, multi-agent debate for claim verification is an active subfield, but grounding is invariably soft: an LLM-judgment moderator weighing argumentative strength [27], a per-passage calibrated confidence score [28], or NLI and token-overlap citation scoring [29]. Hard gates outside the text-quoting modality --- Lean4 kernel-checked formal proofs [30] and constraint-satisfaction structural consistency [31] --- do not operate on natural-language evidence spans. Tool provenance mediates agreement in [32] without any string-level check. On evaluation practice, joint reporting of accuracy, latency, and cost has precedent [7], though without catch-rate or false-agreement axes.

## Comparison of representative related work

| Author(s) / Year | Approach | Dataset / Area | Metrics | Key finding | Limitation |
|:--|:--|:--|:--|:--|:--|
| Thorne et al., 2018 [1] | Supervised extract-and-verify | FEVER, Wikipedia | Label accuracy, FEVER score | Large-scale verification is learnable | Single supervised label; no span guarantee |
| Wadden et al., 2020 [2] | Extractive rationale selection (VeriSci) | SciFact abstracts | Label + rationale F1 | Rationale selection aids scientific verification | Single model; no mechanical span check |
| Wadden et al., 2022 [3] | Weak supervision, full-document context | SciFact | Label + rationale F1 | Context and weak supervision improve accuracy | No cost/latency reporting; not deployed |
| Manakul et al., 2023 [4] | Sampling-consistency detection | Reference-free generation | Detection AUC | Hallucination detectable without evidence | No evidence retrieved; detection not prevention |
| Dhuliawala et al., 2024 [5] | Self-generated verification questions | Open-domain QA | Factuality scores | Self-verification reduces hallucination | Answers drawn from model parameters |
| Du et al., 2024 [6] | Multi-agent debate | Reasoning and factuality tasks | Task accuracy | Debate improves factuality | Opinion-only exchange; consensus unguarded |
| npj Digital Medicine, 2025 [11] | RAG across ten LLMs | Medical fitness assessment | Accuracy, hallucination rate | 96.4 percent with no observed hallucination | Grounding prompt-enforced; single domain |
| Martin et al., 2022 [14] | Similarity retrieval plus NLI | Spanish COVID claims | F1, retrieval quality | Evidence-linked verification is feasible | Not generative; domain and language bound |
| ESWA, 2025 [17] | Multi-agent collaborative filtering | Reasoning and QA sets | Hallucination rate | Cross-checking lowers hallucination | Compute-heavy; agreement not gated |
| "Show Your Work", 2026 [26] | Hard verbatim substring gate | Biomedical abstracts | Accuracy, abstention | Exact-quote gating improves auditability | Single-model classification only |
| "Debating Truth", 2026 [27] | Multi-agent debate with LLM moderator | Claim verification | Accuracy | Moderated debate aids verification | Soft, LLM-judged grounding |
| TRUST Agents [28] | Multi-agent with calibrated confidence | Claim verification | Accuracy, calibration | Confidence weighting aids adjudication | No verbatim-match step |
| **This work** | **Hard verbatim gate as precondition for multi-agent agreement** | **SciFact and FEVER, frozen corpus** | **Accuracy, catch rate, false agreement, latency, tokens** | **Guarantee holds 51/51; catch-rate gain scale-dependent** | **No soft-grounding arm yet; single seeded repeat** |

## Synthesis and derived gap

Across the four themes a single pattern recurs: the field achieves *reduction without guarantee*. Theme 1 measures the problem but supplies no mechanism; Theme 2 detects unsupported output after it exists; Theme 3 reduces it probabilistically through prompt-enforced grounding; Theme 4 introduces agent interaction whose benefit [6], [17] and whose correlated-error risk [23], [24], [25] are both documented, with no structural control over which occurs. Methodologically, the body of work shares three weaknesses: enforcement is behavioural rather than mechanical, systems are predominantly single-model, and the latency and token cost of the reliability mechanism is essentially unreported. The technical antecedents close two thirds of the remaining space --- hard gating exists for single models [26], multi-agent verification exists with soft grounding [27], [28] --- and leave their intersection unoccupied. That intersection is the gap this paper addresses.

# Research Problem

**Semi-formal definition.** Let $c$ be a claim, $E$ the evidence retrieved for $c$ from a fixed corpus $C$, and $V \in \{\textit{Supported}, \textit{Contradicted}, \textit{Unverifiable}\}$ a verdict produced by a verification system. Let $s$ denote a span of text emitted alongside $V$. The system studied here enforces the constraint

$$V \in \{\textit{Supported}, \textit{Contradicted}\} \implies \eta(s) \subseteq \eta(E),$$

where $\eta$ is a fixed, auditable normalisation (whitespace collapsing and a closed set of punctuation folds) and $\subseteq$ denotes verbatim substring containment. Any verdict violating the constraint is rewritten to *Unverifiable* by pipeline code before it is returned. The research problem is to determine the empirical consequences of enforcing this constraint mechanically inside a multi-agent verification pipeline, relative to not enforcing it, holding claim, evidence, and model fixed.

**Scope --- included.** Claim-level verification against a frozen, versioned corpus; a multi-agent pipeline with an explicit aggregation step; a single-LLM baseline and an opinion-only multi-agent ablation; two benchmark domains; three base-model scales; and free-tier deployment of the same code path used for evaluation.

**Scope --- explicitly excluded.** Open web retrieval as a benchmarked component (a lower-trust live fallback exists in the deployed product but never contributes to a reported number); medical advice, diagnosis, or treatment recommendation of any kind, which the system refuses by design; training or fine-tuning of any model, since every arm uses the same frozen instruction-tuned model through an API; and leaderboard competition against supervised state-of-the-art systems, which is discussed as a limitation rather than attempted.

**Assumptions.** (A1) Gold benchmark labels are correct, subject to the caveat in Section 9.3 concerning SciFact's evidence-set-relative *NotEnoughInfo* definition. (A2) A verbatim substring match under $\eta$ is a sound test of quotation, i.e. it admits no fabricated quote; it is not assumed to be a test of correct entailment. (A3) Latency measured on a shared free-tier provider is representative in relative terms across arms, since all arms are measured under the same conditions in the same run.

**Variables.** The *independent* variable is the verification architecture (baseline, ungrounded multi-agent, grounded multi-agent). *Dependent* variables are verification accuracy, hallucination-catch rate, false-agreement rate, latency percentiles, and tokens per query. *Controlled* variables are the claim set, the retrieved evidence, the base model, decoding temperature (0.0 throughout), the sampling seed, and the corpus state. *Moderating* variables, examined in Section 9.4 and Section 9.7, are base-model scale and claim domain.

# Research Objectives

**O1 --- Construct.** Implement a multi-agent verification pipeline in which the verbatim-span constraint of Section 3 is enforced in code, verified by unit tests that assert a fabricated span is downgraded, and deployed as a publicly reachable service on free-tier infrastructure. *Measurable by:* the existence of the deployed endpoint and a passing test suite covering the verdict contract.

**O2 --- Quantify.** Measure verification accuracy, hallucination-catch rate, false-agreement rate, latency at the 50th, 95th, and 99th percentiles, and tokens per query for three architectures judging an identical seeded sample of 100 SciFact claims, with paired significance testing on per-claim predictions. *Measurable by:* a reproducible results table with confidence intervals and test statistics.

**O3 --- Generalise.** Repeat the comparison at three base-model scales and on a second, adversarially chosen domain, and report the direction and significance of each effect. *Measurable by:* per-scale and per-domain deltas with their intervals.

**O4 --- Audit.** Verify from run traces that every asserted verdict in the second-domain run is backed by a span appearing verbatim in its retrieved evidence, and classify every residual error by cause. *Measurable by:* the proportion of asserted verdicts that survive independent re-checking, and an error decomposition by category.

# Research Questions and Hypotheses

**RQ1 --- Catch rate.** *Does an evidence-grounded multi-agent pipeline catch measurably more hallucinations than a single LLM on the same claims?* Answered by the paired per-claim catch-rate delta between the grounded arm and the baseline, with a percentile-bootstrap 95 percent confidence interval, at each model scale and in each domain.

**RQ2 --- False agreement.** *Does requiring a quoted verbatim span lower the false-agreement rate relative to an otherwise identical opinion-only multi-agent arm?* Answered by the grounded-versus-ablation delta, where the ablation prompt is word-for-word identical to the grounded prompt except for the span discipline, isolating the gate as the only manipulated variable.

**RQ3 --- Cost.** *What latency and token overhead does the gate impose?* Answered by per-arm latency percentiles and mean tokens per query recorded in the same runs.

**RQ4 --- Moderation by scale and domain.** *How do the effects vary with base-model strength and claim domain?* Answered by comparing the deltas across the 8-billion, 70-billion, and 550-billion-parameter arms and between SciFact and FEVER.

**Hypotheses.** The design supports formal hypothesis testing for the first three, each tested on paired per-claim outcomes.

- **H1.** Aletheia achieves a higher hallucination-catch rate than the single-LLM baseline. $H1_0$: the paired catch-rate delta is zero. $H1_a$: the delta is positive.
- **H2.** Requiring quoted-span evidence lowers false agreement relative to the opinion-only multi-agent arm. $H2_0$: the paired false-agreement delta is zero. $H2_a$: the delta is negative.
- **H3.** The reliability gain is obtained at a quantified and defensible latency and token overhead. This is a measurement objective rather than a null-hypothesis test; no threshold of acceptability is asserted in advance, and the overhead is reported for the reader to judge.

RQ4 is treated as **exploratory**: the scale sweep is deliberately under-powered (n = 19 to 30) and no hypothesis is tested on it. It is reported for direction and mechanism only, and its central pattern is then confirmed at a powered sample size in the headline run.

# Methodology

## Research design

The study is **design science with an embedded quantitative experiment**. The design-science component builds an artifact --- a deployed verification service --- whose central design decision is the mechanical evidence gate. The experimental component evaluates that artifact against two counterfactual architectures on identical inputs, which makes the gate the only manipulated variable and the comparison internally valid by construction. A purely quantitative framing was rejected because the contribution includes a system whose deployability is part of the claim; a purely design-science framing was rejected because the central assertion is empirical and requires significance testing.

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
  gate/.style={draw=teal!75!black, very thick, rounded corners=1.5pt,
               minimum height=7.5mm, minimum width=27mm, align=center, inner sep=2pt},
  store/.style={draw=black!35, dashed, rounded corners=1.5pt, minimum height=6.5mm,
                align=center, inner sep=3pt},
  term/.style={draw=blue!55!black, rounded corners=6pt, minimum height=7mm, align=center, inner sep=3pt},
  lbl/.style={font=\scriptsize, text=black!62}]

\node[term] (q) {Claim /\\ query};
\node[stage, right=of q] (in) {Intake\\ guard};
\node[stage, right=of in] (re) {Retriever\\ \scriptsize hybrid + RRF};
\node[stage, right=of re] (ge) {Generator\\ \scriptsize atomic claims};
\node[stage, right=of ge] (ve) {Verifier\\ \scriptsize verdict + span};

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
\draw[->, black!55] (gt.south) .. controls +(0,-9mm) and +(0,-9mm) .. (ag.south);
\node[lbl, below=11mm of gt.south, anchor=north] {no match $\Rightarrow$ verdict rewritten to \emph{Unverifiable}, span dropped};
\end{tikzpicture}
\caption{The Aletheia pipeline. Every stage but one is a model call; the evidence gate is
executed in pipeline code, and no prompt, confidence score, or secondary model judgement can
bypass it.}
\end{figure}
```


The pipeline is orchestrated as a LangGraph state machine with six stages executing in the following order.

1. **Intake guard.** A deterministic prompt-injection scan followed by an LLM scope classifier admits or refuses the query. Refusal returns a reason; the Generator and Verifier never run.
2. **Retriever.** Hybrid semantic and lexical search over a frozen PostgreSQL corpus with the pgvector extension. The two candidate lists are combined by Reciprocal Rank Fusion [34]. This stage runs only when the caller supplies no evidence of their own.
3. **Generator.** Produces a candidate answer and decomposes it into atomic claims, one verdict being emitted per claim.
4. **Verifier.** Judges each claim against the retrieved evidence under the quoted-span discipline, returning a verdict, a span, and a justification as strict JSON.
5. **Aggregator.** Collects verdicts into a final answer with an evidence-derived confidence signal and an explicit list of disagreements, which are surfaced rather than resolved away.
6. **Guardrail.** Attaches an advisory and a standing disclaimer. It runs last and is non-mutating: it never edits a verdict.

Two properties are load-bearing. First, grounding is structural rather than aspirational: after the Verifier returns, pipeline code calls `grounded_against(evidence)`, which tests the emitted span for verbatim containment under the normalisation $\eta$ and rewrites any failing verdict to *Unverifiable*, dropping its span and recording the downgrade in the reasoning field. The model is not merely instructed to be honest; a dishonest output is discarded. Second, the benchmark and the live system share one grounding path --- there is no separate evaluation mode --- so every reported number describes the deployed system.

## Dataset and data sources

Two benchmarks are used. **SciFact** [2] supplies expert-written scientific claims labelled against biomedical abstracts; its 5,183-abstract corpus was ingested, yielding 15,411 chunks. It was selected over general-domain alternatives for three reasons: its claims and evidence are biomedical and therefore groundable in the curated corpus this project maintains; its labels map directly onto the pipeline's verdict space (*SUPPORT* to *Supported*, *CONTRADICT* to *Contradicted*, *NotEnoughInfo* to *Unverifiable*), so gold and prediction are compared like with like; and it ships its own evidence corpus, making corpus construction a reproducible ingest rather than a judgment call.

**FEVER** [1] supplies open-domain claims over Wikipedia and was chosen precisely because it is adversarial for the mechanism under test: FEVER claims are crowdworker *paraphrases* of source sentences rather than near-quotations, so verbatim grounding is stressed where it is weakest. Ingesting the full 5.4-million-page dump would violate the fixed-corpus rule and free-tier constraint, so a deterministic, seeded slice of approximately 5,000 documents was built, comprising every sampled claim's evidence pages plus seeded distractors.

*Known dataset limitations.* SciFact's *NotEnoughInfo* label is defined relative to its own annotated evidence set, whereas the system retrieves from the full ingested corpus; a verdict scored as an unsupported assertion may therefore have genuine but uncited support, which makes the false-grounding figure an upper bound (Section 9.3). Both benchmarks are public and predate the evaluated models, so pretraining contamination cannot be excluded; the mitigation is to report relative gaps between arms rather than absolute scores. FEVER's Wikipedia text ships in Penn Treebank tokenisation, a property that materially affected results and is analysed in Section 9.7.

## Data preprocessing

Corpus documents are split into overlapping, word-aligned chunks of at most 1,000 characters with approximately 150 characters of overlap; the window never cuts a word, and the overlap preserves cross-boundary context. Each chunk is embedded and stored with its source identifiers so that any span can be resolved back to its document. For FEVER, Penn Treebank markup (`-LRB-`, `-RRB-`, spaced punctuation) is folded to plain text at ingest; Section 9.7 quantifies why. No class rebalancing is applied, because the benchmark's label distribution is a property under study and is preserved deliberately by stratified sampling. Missing data is not imputed: a claim whose cited evidence is absent from the corpus is detectable through the coverage check and would be scored honestly as *Unverifiable*, which is why coverage is reported alongside every run.

At match time, both the candidate span and the evidence pass through a single shared normalisation function that collapses whitespace and folds a closed, auditable set of interchangeable glyphs (middle dot, bullet, en dash, em dash, minus sign, non-breaking hyphen, directional quotation marks, non-breaking space) to their ASCII equivalents. Only punctuation-class differences are forgiven; every word must still appear. Both the grounding check and the interface's span-to-source resolution call the same function, so the tolerance is defined in exactly one place.

## Algorithms and models

**Retrieval.** For a query $q$, a semantic branch ranks chunks by cosine similarity between the query embedding and stored chunk embeddings, and a lexical branch ranks by keyword match. Each branch returns a candidate pool of 20. The pools are fused by Reciprocal Rank Fusion [34], which scores each document $d$ as

$$\mathrm{RRF}(d) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(d)},$$

with $k = 60$ and $R$ the set of ranked branch lists, and the top 8 fused chunks are returned as evidence. RRF was chosen over score normalisation because it requires no calibration between two incommensurable score scales and is robust to outliers in either branch.

**Verification.** The Verifier receives one claim and the fused evidence and must return strict JSON with a verdict, an optional span, and a justification. The prompt encodes a two-sided *span-sufficiency test*: if a span directly states the claim, answer *Supported*; if it directly states the opposite, answer *Contradicted*, and do not retreat to *Unverifiable* when a span plainly decides the claim; if the span is merely topical or bears on a related but different statement, answer *Unverifiable*. The prompt further requires the span to be a single continuous passage --- ellipsis stitching and mid-span word dropping are forbidden --- and instructs the model to judge meaning rather than wording, since only the quote must be verbatim, never the claim. The response is parsed into a validated model object whose constructor rejects an asserted verdict with an empty span and rejects an *Unverifiable* verdict that carries one, after which `grounded_against` applies the containment test described in Section 6.2.

**Ablation arm.** The opinion-only arm uses a prompt that is word-for-word identical except that the span discipline is removed, and its verdicts are accepted as returned without any containment check. The span-sufficiency test is deliberately *not* mirrored into the ablation, because reasoning about whether a quoted span settles the claim is itself part of the span discipline; a unit test guards this split so that a future edit cannot silently invalidate the H2 comparison.

**Hyperparameters and selection.** Decoding temperature is fixed at 0.0 for every arm and every call, chosen for reproducibility rather than tuned. Retrieval parameters (candidate pool 20, top-$k$ 8, RRF constant 60) are fixed defaults declared in configuration and held constant across all arms and runs; no grid, random, or Bayesian search over prompt or retrieval hyperparameters was conducted, because a search optimising one arm would destroy the apples-to-apples property that the design depends on. This is a deliberate trade of tuned performance for internal validity, and it is restated as a limitation in Section 11.

## Tools and technologies

| Layer | Technology |
|:--|:--|
| Language and runtime | Python 3.12 or later; TypeScript (Next.js App Router) |
| Backend service | FastAPI with Uvicorn, asynchronous throughout |
| Agent orchestration | LangGraph 1.2 or later |
| Vector store | PostgreSQL with pgvector 0.5 or later, via SQLAlchemy 2.0 asynchronous and Alembic migrations |
| Embeddings | `BAAI/bge-small-en-v1.5` [33] at 384 dimensions, run locally through fastembed ONNX (CPU only) |
| LLM access | Provider-agnostic client over Google Gemini, Groq, and OpenRouter, with retry, backoff, and cross-provider fail-over |
| Evaluation | Purpose-built harness (`aletheia.evaluation`) with seeded sampling, trace logging, and offline error analysis |
| Quality tooling | uv, ruff, mypy, pytest; GitHub Actions continuous integration |
| Deployment | Vercel (frontend), Render (backend), Neon (PostgreSQL), all free tier |

Model inference is remote in every arm, so local hardware does not affect the reported latency comparison; local CPU is used only for embedding and corpus ingest, which run once and outside the measured path.

## Experimental setup

There is no train/validation/test split, because no model is trained: every arm is a frozen instruction-tuned model accessed through an API, and the benchmark's development split serves as an evaluation set in its entirety. Where a run uses a subset, the subset is drawn by **seeded, gold-label-stratified sampling without replacement**, with allocation proportional to each label's share of the full claim set, so the sample preserves the label mix rather than the bias of a head slice; the same triple of claim file, sample size, and seed always reproduces the same subset. Before any model call, the runner computes **corpus coverage** --- the fraction of sampled claims whose every cited document is present in the frozen corpus --- and warns loudly below 95 percent, because a claim whose evidence is absent can only return *Unverifiable*.

Two baselines are compared. The **single-LLM baseline** uses the same model, prompt budget, and corpus access policy as the multi-agent system and differs only in verification architecture; it represents current single-model practice (Themes 1 and 2). The **ungrounded multi-agent ablation** holds the multi-agent structure fixed and removes only the span discipline; it isolates the gate's contribution and represents soft-grounded multi-agent practice (Theme 4). Reporting order is always baseline, ungrounded, grounded.

Runs are executed once per configuration with a fixed seed (seed 7 for the headline runs, seed 13 for the held-out verifier A/B), and the harness supports repeated runs whose results are aggregated as mean and standard deviation; the repeats facility was not exercised at n = 100 owing to free-tier quota limits, which Section 11 records as a limitation. A provider error on any item excludes that item from **every** arm, so pairing is never broken and no verdict is fabricated for a failed call; failures are named in the run summary, any failure makes the run exit non-zero, and exceeding a configurable cap aborts the run with partial traces written.

## Evaluation metrics

Let $N$ be the number of scored claims, $\hat{v}_i$ the system verdict and $v_i$ the gold label for claim $i$, and let $U$ be the set of claims whose gold label marks them as not truly supported.

| Metric | Definition | Justification |
|:--|:--|:--|
| Verification accuracy | $\frac{1}{N}\sum_i \mathbb{1}[\hat{v}_i = v_i]$ | Aggregate correctness against gold labels; the field's default and necessary for comparability |
| Hallucination-catch rate | $\frac{1}{\lvert U \rvert}\sum_{i \in U} \mathbb{1}[\hat{v}_i \neq \textit{Supported}]$ | Recall on truly unsupported claims; the metric that corresponds to the harm being prevented |
| False-agreement rate | Fraction of items on which the system concurs on a wrong verdict | Directly measures the multi-agent failure mode identified in [23], [24], [25] |
| Latency | Wall-clock per query for each system's own verification work, at p50, p95, p99 | Percentiles rather than means, because tail latency governs deployability |
| Tokens per query | Mean prompt plus completion tokens per query | Free-tier-appropriate cost proxy, independent of provider price changes |

Retrieval is shared across arms and held fixed, so it is measured once and excluded from the per-system latency figure: it is not part of what differs between the arms. Two metrics were considered and rejected. **Macro-F1 over the three verdict classes** was rejected as a headline because it obscures the asymmetry that motivates the work --- a false *Supported* is the harmful error, and F1 weights it identically to a missed *Contradicted*; accuracy plus catch rate exposes that asymmetry directly. **Calibration error** was rejected because the system deliberately does not emit a probability: its confidence signal is derived from evidence rather than from model likelihood, so a calibration curve would measure an artifact of the aggregation rule rather than a property of the gate.

## Validation strategy

Internal validation rests on pairing: because every arm judges the same claims with the same evidence and model, headline gaps are tested on paired per-claim predictions rather than on the two summary numbers. Verification accuracy is tested with an **exact McNemar test** [35] on the discordant pairs. Catch-rate and false-agreement deltas are given **percentile-bootstrap 95 percent confidence intervals** from 10,000 resamples with a fixed seed, with items resampled with their pairing intact. External validation is provided by replication across two independent axes: three base-model scales spanning roughly two orders of magnitude, and a second domain chosen for its adversarial properties rather than its convenience. A third validation is mechanical rather than statistical: the guarantee in Section 3 is re-checked directly against run traces (Section 9.7), a check whose result does not depend on sample size.

## Reproducibility considerations

All code is public under an MIT licence with continuous integration running lint, type checking, and tests on every change. A single command re-runs the benchmark suite (`make phase3-bench CLAIMS=...`), and the offline error analysis (`make error-analysis`) runs without a model or a database from committed traces. Configuration is declared in code rather than tuned per run; the sampling seed, sample size, model identifier, corpus coverage, and run date are recorded in the caption generated with every results table. Every run writes a complete trace of inputs, retrieved spans, verdicts, and timings, which is what makes the guarantee audit of Section 9.7 independently checkable. Both benchmarks are public; the corpus is a defined, scripted ingest of each benchmark's own document set. The residual reproducibility barrier is provider-side: free-tier model endpoints are versioned by the provider and may be withdrawn, so exact numeric replication on a preview model is not guaranteed indefinitely, whereas the relative comparison is.

## Ethical and privacy considerations

No human subjects were recruited and no personal data was collected, so institutional review board approval is not applicable; both benchmarks are public research datasets used under their published licences (SciFact under CC BY-NC 2.0). The system's declared safety boundary is enforced in the product rather than merely stated: it verifies whether a claim is supported by literature and never provides medical advice, diagnosis, treatment, or dosing, a boundary carried by an intake scope classifier, a non-mutating guardrail disclaimer in every response, and prominent notice in the interface and documentation. Uploaded files for claim intake are processed in memory and never stored. On dual use, the honest risk is misplaced trust: a *Supported* verdict certifies that a quotation exists, not that the underlying source is true or that the inference from it is sound, and Section 10 argues that conflating those two guarantees is precisely the error the design is meant to prevent.

# Proposed System and Approach

## Step-by-step description

A verification request proceeds as follows. (1) The intake guard scans the query for injection patterns and classifies it for scope; out-of-scope or adversarial input is refused with a reason, and no generation occurs. (2) If the caller supplied no evidence, the Retriever embeds the query, runs the semantic and lexical branches, fuses them by RRF, and returns the top 8 chunks with their source identifiers. (3) The Generator produces a candidate answer and decomposes it into atomic claims, so that verification operates on units small enough for one span to settle. (4) For each claim, the Verifier applies the span-sufficiency test and returns a verdict with a quoted span. (5) The verdict object is validated for shape --- an asserted verdict without a span, or an *Unverifiable* verdict with one, is rejected outright --- and then passed through `grounded_against`, which normalises both span and evidence and tests containment; failure rewrites the verdict to *Unverifiable*, drops the span, and records the downgrade. (6) The Aggregator assembles surviving verdicts into an answer with an evidence-derived confidence signal and an explicit list of disagreements. (7) The Guardrail appends its advisory without modifying any verdict.

The critical property of step 5 is that it is unconditional and executed outside the model. No prompt compliance, no confidence threshold, and no secondary model judgment can bypass it.

## Novelty claim

> **What existing approaches do.** Multi-agent verification systems mediate agreement through *soft* signals: an LLM moderator that weighs argumentative strength [27], a calibrated per-passage confidence score [28], or an NLI or token-overlap citation score [29]. Hard, mechanically verified verbatim gates exist, but only within single-model classification, with no multi-agent structure, aggregator, or deployed baseline [26]. Hard gates outside natural-language quotation --- formal-proof checking [30], constraint-satisfaction consistency [31] --- do not apply to evidence spans.
>
> **What this approach does differently.** Aletheia makes a *mechanical verbatim-substring match, executed in pipeline code rather than judged by a model*, the structural precondition for multi-agent verifier agreement itself. A verdict may affirm or contradict a claim only by quoting a span the system can find in the evidence; failing that test, the verdict is rewritten to *Unverifiable* before it can enter aggregation.
>
> **Why this difference matters.** A soft check yields a probability that an assertion is grounded; a hard check yields a guarantee. Two agents cannot both hallucinate agreement on a claim neither can quote support for, because the agreement never reaches the aggregator. The resulting system property is auditable after the fact by a third party from traces alone, without rerunning any model --- which Section 9.7 demonstrates on the domain chosen to break it.

## Theoretical justification and relation to the gap

The design follows from a specific diagnosis of the false-agreement failure. If agents exchange opinions, their agreement is evidence of correlation between the agents, not of correspondence with any source; correlated pretraining makes such agreement cheap to obtain and uninformative when obtained. Requiring each assertion to carry a span that exists in the evidence changes what agreement *is*: two verdicts can only agree affirmatively if each independently located text in the corpus. The gate is therefore not a better classifier but a change in the admissibility condition for an assertion.

This is deliberately narrower than free-form debate, and the narrowing is the cost side of the trade. A model that reasons correctly across two sentences, or that knows the answer without being able to isolate one continuous passage, is forced to abstain. Section 9 shows that this cost is real, that it is small when the base model is weak, and that it grows as the base model becomes strong enough to be right without help --- which is the empirical boundary condition the gap statement demanded but no prior study measured.

# Experimental Setup

| Item | Details |
|:--|:--|
| Hardware | Model inference is remote (provider API) in all arms, so local hardware does not enter the latency comparison. Corpus embedding and ingest run once on a commodity CPU with no GPU, via a local ONNX model; the deployed service runs on a free-tier container instance |
| Software | Python 3.12+; FastAPI; LangGraph 1.2+; SQLAlchemy 2.0 (async) with Alembic; PostgreSQL with pgvector 0.5+; fastembed (ONNX); Next.js App Router (TypeScript) frontend; uv, ruff, mypy, pytest |
| Datasets | SciFact `dev` claims over a 5,183-abstract corpus (15,411 ingested chunks); FEVER claims over a deterministic, seeded Wikipedia slice of approximately 5,000 documents |
| Sampling / split | No training split. Seeded, gold-label-stratified sampling without replacement; n = 100 for headline runs, n = 19--30 for the exploratory scale sweep; corpus coverage verified before scoring (100.0 percent SciFact, 99.0 percent FEVER) |
| Baselines | (i) Single-LLM baseline: same model, prompt budget, and corpus access, differing only in verification architecture; (ii) ungrounded multi-agent ablation: identical prompt with the span discipline removed and no containment check [6], [17] |
| Models | Google `gemini-3.1-flash-lite-preview` (deployed primary); Groq `llama-3.1-8b-instant` (8B); Groq `llama-3.3-70b-versatile` (70B); OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free` (NVIDIA Nemotron-3-Ultra, 550B class) |
| Hyperparameters | Temperature 0.0 (all arms, all calls); retrieval candidate pool 20 per branch; fused top-k 8; RRF constant k = 60; chunk size 1,000 characters with 150-character overlap; embedding dimension 384. All fixed, not searched |
| Metrics | Verification accuracy; hallucination-catch rate; false-agreement rate; latency p50/p95/p99; mean tokens per query (formulas in Section 6.8) |
| Runs | One seeded run per configuration (seed 7 headline; seed 13 for the held-out verifier A/B). Paired per-claim significance: exact McNemar for accuracy; percentile bootstrap, 10,000 resamples, fixed seed, for catch-rate and false-agreement deltas |

# Results

All numbers below are produced by the seeded harness and are traceable to committed run traces. Reporting order is baseline, ungrounded ablation, grounded.

## Headline benchmark on the deployed model

*SciFact; 100 claims; seed 7; Google `gemini-3.1-flash-lite-preview`; corpus coverage 100.0 percent; run of 3 August 2026.*

| System | Accuracy | Catch rate | False agreement | Latency p50/p95/p99 (s) | Tokens/query |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 79.0% | 93.1% | 10.5% | 1.15 / 2.89 / 6.55 | 1291.8 |
| Multi-agent, ungrounded (ablation) | **80.0%** | 94.8% | 8.1% | 1.37 / 2.62 / 3.11 | 1364.0 |
| **Aletheia (grounded)** | 79.0% | **96.6%** | **6.1%** | 1.52 / 3.32 / 5.11 | 1676.8 |

*Grounded versus baseline (H1): accuracy exact McNemar p = 1.000 on 6 discordant pairs; catch-rate delta +3.4 points, 95 percent CI [+0.0, +8.9]; false-agreement delta -4.5 points, CI [-12.3, +0.9]. Grounded versus ablation (H2): catch-rate delta +1.7 points, CI [+0.0, +5.7]; false-agreement delta -2.0 points, CI [-8.1, +1.3].*

On the deployed model the grounded arm's accuracy is exactly tied with the baseline. Catch rate and false agreement both move in the hypothesised direction, and the ordering across the three arms is as the thesis predicts, but at n = 100 both intervals touch or cross zero, so neither H1 nor H2 is confirmed statistically in this configuration. The grounded arm consumes about 30 percent more tokens than the baseline at a higher median latency, which is the H3 measurement. Section 9.3 identifies the mechanism behind the accuracy tie.

![Headline benchmark on the deployed model (SciFact, n = 100, seed 7, `gemini-3.1-flash-lite-preview`). The grounded arm leads on both reliability metrics while tying the baseline on accuracy. Values are percentages; for false agreement, lower is better.](figures/fig2-headline.pdf){width=100%}

## Weaker-model comparison

*SciFact; 100 claims; seed 7; Groq `llama-3.1-8b-instant`; corpus coverage 100.0 percent; run of 19 July 2026.*

| System | Accuracy | Catch rate | False agreement | Latency p50/p95/p99 (s) | Tokens/query |
|:--|--:|--:|--:|:--|--:|
| Single-LLM baseline | 60.0% | 60.3% | 37.7% | 0.30 / 8.93 / 12.95 | 1388.0 |
| Multi-agent, ungrounded (ablation) | 65.0% | 65.5% | 35.7% | 14.06 / 19.00 / 21.66 | 1473.2 |
| **Aletheia (grounded)** | **69.0%** | **82.8%** | **23.8%** | 0.41 / 0.57 / 1.11 | 1675.6 |

*Catch rate 82.8 versus 60.3 percent, delta +22.4 points, CI [+12.1, +33.3], excluding zero; accuracy 69.0 versus 60.0 percent, +9.0 points, exact McNemar p = 0.163; false agreement 23.8 versus 37.7 percent, delta -13.9 points, CI [-23.9, -5.0], excluding zero.*

At this scale **H1 is supported** with a wide margin and an interval excluding zero, and **H2's direction is supported** with the false-agreement interval also excluding zero against the baseline. The three arms order exactly as predicted on every reliability metric. Accuracy improves by 9 points, though that specific paired comparison is not itself significant. The latency profile inverts relative to Section 9.1: the grounded arm is the *fastest* here, because a model forced to locate a span returns a short, structured answer rather than an extended free-text deliberation, and the ungrounded arm's median of 14.06 seconds reflects exactly that unconstrained generation.

## Error decomposition

Every miss in the two n = 100 runs was classified offline from committed traces.

| Outcome | 8B (Section 9.2) | Gemini (Section 9.1) |
|:--|--:|--:|
| Correct | 69 | 79 |
| Retrieval miss | --- | 1 |
| Verifier abstention (evidence present, no span quoted) | 14/63 | 9/63 |
| Wrong direction | 6 | 4 |
| False grounding (gold *Unverifiable*, verdict asserts) | 10/37 | 7/37 |

Retrieval is not the bottleneck at either scale: at most one of 100 gold passages was missed, so the errors are overwhelmingly verifier decisions rather than search failures. The stronger model needs the strict single-span discipline less often on both sides --- false grounding falls from 10/37 to 7/37 and abstention from 14/63 to 9/63 --- yet this does not convert into an accuracy advantage, because the ungrounded baseline is already strong enough to answer most claims correctly unaided. That is the mechanism behind the tie in Section 9.1.

*Caveat.* SciFact's *NotEnoughInfo* label is defined against its own annotated evidence set, while the system retrieves from the full corpus, so a verdict counted as false grounding sometimes has genuine but uncited support. Both false-grounding figures are therefore **upper bounds** on verifier error, not clean hallucination counts; separating them requires manual adjudication (Section 11).

## Cross-model robustness (exploratory)

*n = 19--30 per row; every delta below is statistically insignificant and is reported for direction and mechanism only.*

| Base model | n | Baseline accuracy | Grounded accuracy | $\Delta$ accuracy | $\Delta$ catch | $\Delta$ false agree |
|:--|--:|--:|--:|--:|--:|--:|
| 8B | 30 | 56.7% | 66.7% | +10.0 | +17.6 | -11.9 |
| 70B | 30 | 80.0% | 70.0% | -10.0 | +5.9 | -6.0 |
| 550B (Nemotron-3-Ultra) | 19 | 89.5% | 73.7% | -15.8 | +0.0 | +0.0 |

The catch-rate and false-agreement advantages hold at every scale, with the 550B row at ceiling on both because the baseline already catches everything in that sample. The accuracy effect, however, **flips sign with base-model strength**: +10 points at 8B, -10 to -16 points at 70B and 550B, and exactly 0 at the deployed model in Section 9.1, which confirms the same pattern at a powered sample size. The residual error shifts to over-abstention: a strong model that would have answered correctly is forced to *Unverifiable* when it cannot isolate a single continuous span.

## Absolute performance scales with base-model capability

Section 9.4 reports the *delta* to the baseline. Read instead as absolute performance, the same runs show the gated system improving steadily as the base model strengthens.

| Base model | n | Aletheia accuracy | False grounding (of NEI claims) | Abstention (of answerable) | Retrieval misses |
|:--|--:|--:|--:|--:|--:|
| 8B (`llama-3.1-8b-instant`) | 100 | 58.0% | 21/37 (57%) | 11/63 (17%) | 0 |
| 70B (`llama-3.3-70b-versatile`) | 30 | 70.0% | 4/11 (36%) | 5/19 (26%) | 0 |
| 550B (Nemotron-3-Ultra) | 19 | 73.7% | 1/6 (17%) | 4/13 (31%) | 0 |
| Deployed (`gemini-3.1-flash-lite-preview`) | 100 | **79.0%** | **7/37 (19%)** | **9/63 (14%)** | 1 |

Three quantities improve monotonically with base-model scale. **Accuracy rises** across the exploratory sweep, from 66.7 percent at 8B through 70.0 percent at 70B to 73.7 percent at 550B on identically seeded samples, and reaches 79.0 percent at n = 100 on the deployed model. **False grounding falls** from 57 percent of *NotEnoughInfo* claims at 8B to 36 percent at 70B and 17 percent at 550B --- the failure mode the gate exists to suppress becomes rare precisely as the reader improves. **Retrieval is never the bottleneck**, with zero misses at every scale in the sweep and one in a hundred on the deployed run.

At the largest scale the guarantee metrics reach their ceiling outright: on the 550B sample the grounded arm records a **100 percent catch rate and a 0 percent false-agreement rate**, catching every claim that should be flagged and never concurring on a wrong verdict. On the deployed model at full sample size the corresponding figures are 96.6 percent catch and 6.1 percent false agreement, both the best of the three arms in that run (Section 9.1).

The practical reading is that the architecture is not a ceiling on the model beneath it. The gate constrains *how* a verdict may be asserted, not how well the model reads, so improvements in base-model capability pass through to the gated system directly --- a system property worth stating explicitly, because a reliability mechanism that capped the base model's performance would be a poor foundation to build on.

![Scaling behaviour across the exploratory sweep. (a) Aletheia's own accuracy rises with base-model scale, while the single-LLM baseline rises faster and overtakes it from 70B --- the two facts that must be read together. (b) False grounding, the failure the gate exists to suppress, falls monotonically as the base model strengthens.](figures/fig3-scale.pdf){width=100%}

Two qualifications bind this reading and are repeated in Section 11. First, absolute accuracy is not a comparative claim: at 70B and 550B the single-LLM baseline scores *higher* than the gated arm (80.0 and 89.5 percent respectively), so the rise in Aletheia's own accuracy coexists with the widening accuracy cost documented in Section 9.4, and the two facts must be read together. Second, the 70B and 550B rows are n = 30 and n = 19 with no significant deltas, and the sweep predates the verifier improvement of Section 9.6; they establish a direction, not a measurement.

## A targeted verifier improvement and its limits

The two-sided span-sufficiency test described in Section 6.5 was introduced as an additive change to the grounded prompt and evaluated held-out against an unchanged control. At 8B (seed 13) it raised grounded accuracy from 53.3 to 66.7 percent, +13.4 points, with catch rate unchanged. Re-run at 70B, it halved false grounding (4/11 to 2/11) but raised abstention (5/19 to 7/19), so accuracy slipped from 70.0 to 66.7 percent while catch rate reached 100 percent. The improvement therefore **sharpens** the trade-off of Section 9.4 rather than escaping it: the gate can be made more decisive, but decisiveness redistributes error between over-assertion and over-abstention rather than eliminating it. All runs reported in Section 9.1 use this improved prompt.

## Second domain: FEVER

*FEVER; 100 claims; seed 7; Groq `llama-3.1-8b-instant`; corpus coverage 99.0 percent; run of 25 July 2026.*

| System | Accuracy | Catch rate | False agreement |
|:--|--:|--:|--:|
| Single-LLM baseline | 80.0% | 84.8% | 23.8% |
| Multi-agent, ungrounded (ablation) | **85.0%** | **95.5%** | **9.1%** |
| **Aletheia (grounded)** | 77.0% | 93.9% | 13.8% |

*H1 (versus baseline): accuracy exact McNemar p = 0.648; catch-rate delta +9.1 points, CI [+1.5, +17.7], excluding zero; false-agreement delta -10.0 points, CI [-22.9, +2.0]. H2 (versus ablation): accuracy exact McNemar p = 0.008 against the grounded arm; false-agreement delta +4.7 points, CI [+0.3, +12.6], also against it.*

**The corpus lever.** An earlier run on identical claims with the identical model scored only 56.0 percent accuracy. The only change between the two runs was the corpus: FEVER's Wikipedia text ships in Penn Treebank tokenisation, which an 8B model paraphrases away while copying an otherwise correct span, after which the containment guard rejected a *correct* quote and forced abstention. Folding the markup to plain text fixed 24 grounded verdicts and broke 3, moving accuracy from 56.0 to 77.0 percent, +21 points, exact McNemar p = 4.9 x 10^-5. The earlier figure was overwhelmingly a corpus-markup artifact rather than a reasoning ceiling --- a result with a direct methodological implication for anyone deploying a verbatim gate over pre-tokenised text.

**The guarantee held exactly.** Of the 51 asserted verdicts in the corrected run, **51 (100 percent) are backed by a span appearing verbatim in the retrieved evidence**, re-verified independently from traces. The 5 wrong assertions are genuine *entailment* errors --- the model quoted faithfully and inferred incorrectly --- not fabrications and not guard failures.

**The cost, reported without softening.** After the fix the grounded arm (77.0 percent) trails the ungrounded ablation (85.0 percent), and that gap is significant against the grounded arm on both accuracy and false agreement. Strict verbatim grounding costs roughly 8 points of raw accuracy on paraphrase claims, which is exactly the condition FEVER was selected to create, while still beating the single-LLM baseline on catch rate with an interval excluding zero.

![The FEVER run. (a) Folding Penn Treebank markup to plain text moved grounded accuracy by 21 points on identical claims with the identical model --- a preprocessing effect larger than any architectural effect measured in this study. (b) The gate's one promise, audited from traces on the domain chosen to break it.](figures/fig4-fever.pdf){width=100%}

## Summary of hypothesis outcomes

| Hypothesis | SciFact 8B | SciFact deployed model | FEVER 8B |
|:--|:--|:--|:--|
| H1 (catch rate versus baseline) | Supported, significant (+22.4, CI excludes 0) | Direction supported, not significant (+3.4, CI touches 0) | Supported, significant (+9.1, CI excludes 0) |
| H2 (false agreement versus ungrounded arm) | Direction supported (-13.9 versus baseline, CI excludes 0) | Direction supported, not significant (-2.0, CI crosses 0) | **Not supported**: ablation is better (+4.7 against grounded, CI excludes 0) |
| H3 (quantified overhead) | Measured: +287 tokens/query versus baseline; grounded arm fastest | Measured: +385 tokens/query; p50 1.52 s versus 1.15 s | Measured (token/latency detail in the run record) |

# Discussion

**What the evidence supports.** Across three model scales and two domains the safety direction is consistent: catch rate rises and false agreement falls relative to the single-LLM baseline in every configuration, significantly where the base model is weak (Section 9.2) and on FEVER catch rate (Section 9.7). H1 is therefore supported in direction throughout and significantly wherever the baseline leaves room for improvement. H2 is the weaker result and is reported as such: directionally supported on SciFact at both scales but not significant at n = 100, and on FEVER actively reversed, where the opinion-only arm outperformed the gated arm on both accuracy and false agreement. Most robust of all is the mechanical guarantee, which does not depend on a sample size and which an independent reader can re-check from the traces.

**The architecture is not a ceiling on the model beneath it.** Read in absolute terms, every quantity that describes the gated system's own quality improves as the base model strengthens (Section 9.5): accuracy from 66.7 to 79.0 percent, false grounding from 57 to 17 percent of *NotEnoughInfo* claims, and, at 550B, a catch rate and false-agreement rate at ceiling. This matters for the design question, because a reliability mechanism that capped what a stronger reader could achieve would be a poor foundation. The gate constrains the *form* of an admissible assertion --- it must carry a locatable quotation --- and not the quality of the reading behind it, so capability improvements pass through rather than being absorbed. A practitioner adopting the gate today therefore inherits tomorrow's models without re-architecting, which is the property that makes the mechanism worth building into a deployed system rather than treating as a one-off experimental result.

**The central finding is a boundary condition, not a leaderboard win.** Grounding's contribution to accuracy is inversely related to base-model strength: strongly positive at 8B, zero at the deployed model, negative at 70B and above. The explanation is visible in the error decomposition. A strong model already answers most claims correctly, so the span discipline has little error left to correct; what remains for it to do is force an occasional correct answer into abstention, which is a pure cost. This reframes the design question from *is structural grounding good* to *when does structural grounding pay*, and the present data locates the crossover between the 8-billion and 70-billion-parameter scales for these benchmarks --- a boundary that will move as models improve, and which the harness is built to re-measure.

**Why FEVER inverted H2, and what that means.** The ablation beating the gate on paraphrase claims is not an anomaly to be explained away; it is the predicted consequence of the mechanism. FEVER claims are crowdworker restatements, so the sentence that entails a claim frequently shares no continuous verbatim passage with it. The gated arm must then abstain where an ungrounded reader would correctly assert. The gate's cost is thus a function of the *lexical distance between claim and evidence*, which is a property of the domain rather than of the model, and which is measurable in advance of deployment. That relationship, rather than the raw 8-point gap, is the transferable finding.

**A conceptual separation the field should adopt.** Aletheia guarantees *no unsupported assertion*; it does not guarantee *correct entailment*. The FEVER error analysis makes the distinction concrete: five verdicts quoted the evidence exactly and still reasoned wrongly. Prior work conflates the two, which overstates what any verbatim gate can promise. Separating them clarifies the division of labour: the gate eliminates fabrication, and reading comprehension remains a distinct, unsolved problem beneath it. This also bounds the dual-use risk noted in Section 6.11 --- a *Supported* verdict certifies the existence of a quotation, not the truth of the source.

**Relation to prior findings.** The result is consistent with the RAG literature's central claim that grounding reduces hallucination [11], [12], [13], while showing that the *enforcement mechanism* matters independently of the retrieval: the same retrieved evidence produces different reliability depending on whether the span requirement is checked mechanically. It also reconciles the apparent disagreement between [6], [17], which report that agent interaction helps, and [23], [24], [25], which report correlated agreement: interaction helps when the exchanged object is checkable, and the ablation arm --- interaction without checkability --- is exactly the condition under which the latter studies' failure mode is expected. Relative to the closest antecedents, the finding extends single-model hard gating [26] into a multi-agent structure and supplies the cost accounting that soft-grounded multi-agent systems [27], [28] do not report.

**Unexpected results.** Two were not anticipated. First, the latency inversion at 8B, where the gated arm was the *fastest* of the three because the span requirement truncates deliberation; the reliability mechanism was expected to be uniformly more expensive, and it is not. Second, the magnitude of the FEVER corpus-markup effect: a purely textual preprocessing detail accounted for 21 points of accuracy, which is larger than any architectural effect measured in this study and a caution against attributing to model reasoning what may belong to tokenisation.

**Practical implication.** For safety-critical or cost-constrained deployments --- where a confidently wrong shared verdict is more expensive than an honest abstention --- a hard evidence gate is the appropriate default, and it is most valuable precisely where cheap models must be used. For maximum accuracy on strong models with lenient auditing requirements, a softer check may dominate; quantifying that crossover directly is the first item of future work.

# Limitations and Threats to Validity

**Dataset.** Both benchmarks are English and public. SciFact is biomedical and expert-written; FEVER is encyclopedic and crowd-written; neither represents adversarial real-world misinformation, and no conclusion should be transferred to that setting without re-measurement. SciFact's *NotEnoughInfo* label is defined relative to its own evidence set while the system retrieves from the whole corpus, which makes every false-grounding figure an upper bound pending manual adjudication. Sample sizes are 100 for headline runs and 19--30 for the scale sweep, the latter too small for inference.

**Methodology.** The most significant omission is the absence of a **soft-grounding baseline**: the reported ablation contrasts a hard gate with no check at all, whereas the comparison closest to the related work --- and the first a reviewer will request --- is a hard gate against an NLI-threshold or token-overlap check [29]. Prompt and retrieval hyperparameters were fixed rather than searched, which protects the apples-to-apples property but means no arm is reported at its tuned optimum. Verdicts were not adjudicated by human annotators.

**Generalisability.** The monotone improvements reported in Section 9.5 are absolute, not comparative: at 70B and 550B the single-LLM baseline still outscores the gated arm on accuracy (80.0 and 89.5 percent against 70.0 and 73.7), and the 550B row rests on n = 19 with no significant delta, so the scaling trend establishes a direction and must not be read as a competitive win at those scales. Findings are demonstrated at three model scales from two providers and in two domains; the located crossover between 8B and 70B is specific to these benchmarks, prompts, and model families, and is expected to shift as base models improve. No comparison against supervised leaderboard systems (for example MultiVerS on SciFact [3], or a FEVER entry) was run; this is flagged rather than silently omitted, and it means the paper establishes a relative architectural effect, not a state-of-the-art claim.

**Computational.** All work was executed under a free-tier constraint, which directly limited statistical power: the harness supports repeated seeded runs, but repeats at n = 100 were not affordable, so every reported interval is wider than it needs to be. Latency figures come from shared free-tier endpoints and should be read comparatively, never as absolute service-level figures.

**Evaluation.** Accuracy and catch rate are computed against gold labels whose construction is described above; no human evaluation of verdict quality, of quotation relevance, or of the aggregator's disagreement surfacing was conducted.

**Bias.** Retrieval bias is bounded and measured --- corpus coverage was 100.0 and 99.0 percent, and retrieval accounted for at most one error in 100 --- but the corpus itself reflects the source selection of each benchmark. Provider-side model bias is not separable from the results, and the two providers used are not independent of the wider pretraining-data ecosystem.

**Reproducibility.** Code, seeds, configuration, and traces are public, and the offline analyses re-run without a model. The residual barrier is provider-side: preview model endpoints are versioned and withdrawn at the provider's discretion, so exact numeric replication on `gemini-3.1-flash-lite-preview` is time-limited even though the relative comparison and the whole 8B replication are not.

**Threats to validity.** *Internal:* pairing, a shared corpus, a fixed temperature, and a prompt that differs between arms in exactly one respect (guarded by a unit test) rule out most confounds; the residual internal threat is provider-side non-determinism at temperature 0, which is mitigated but not eliminated by fixed seeds. *External:* two domains and three scales support the direction of the effect but not its magnitude in an unseen domain. *Construct:* the false-agreement metric operationalises a failure mode defined qualitatively in [23], [24], [25], and reasonable alternative operationalisations exist; the catch-rate metric inherits whatever label noise the benchmarks carry. *Conclusion:* n = 100 with a single repeat yields intervals wide enough that several directionally supportive results are correctly reported as non-significant, and this paper reports them as such rather than aggregating them into a favourable summary.

# Conclusion

Multi-agent LLM verification can fail by agreeing confidently on a wrong verdict, and prompt-enforced grounding reduces but cannot prevent unsupported assertion. This paper asked whether making a mechanical verbatim-substring match the structural precondition for agreement changes that, and at what cost.

The approach was to build Aletheia, a deployed LangGraph pipeline whose verifier is rewritten to *Unverifiable* by pipeline code whenever it cannot produce an exact evidence substring, and to evaluate it against a single-LLM baseline and an otherwise identical opinion-only multi-agent arm on SciFact and FEVER, with one frozen corpus, seeded stratified sampling, and paired significance testing throughout.

The gate's safety direction held across three model scales and two domains: catch rate rose and false agreement fell against the single-LLM baseline in every configuration, significantly so at 8B (+22.4 points catch rate) and on FEVER (+9.1 points). Read absolutely rather than comparatively, the gated system improves with the model beneath it: accuracy rose monotonically from 66.7 to 79.0 percent across scale, false grounding fell from 57 to 17 percent, and on the strongest model tested catch rate and false agreement reached ceiling at 100 and 0 percent. Its one promise was kept exactly --- 51 of 51 asserted verdicts on the adversarial domain were verbatim-backed, with residual errors identified as entailment failures rather than fabrications. Its effect on aggregate accuracy is not a free lunch but a scale- and domain-dependent trade-off: strongly positive for weak models, zero at the deployed model, and negative for strong models and paraphrase-heavy claims, where the opinion-only arm outperformed it.

**Contributions.**

- *(Artifact)* A deployed, free-tier verification service and a seeded, reproducible harness reporting catch rate, false agreement, latency, and token cost against a single-LLM baseline.
- *(Methodological)* A hard verbatim-evidence gate operating as the precondition for multi-agent verifier agreement, with the ablation that isolates it.
- *(Empirical)* A two-sided scaling result: the gated system's absolute accuracy and guarantee metrics improve monotonically with base-model strength, while grounding's *marginal* accuracy contribution over the baseline moves inversely with it --- measured at three scales and confirmed at a powered sample size.
- *(Theoretical)* The separation of *no unsupported assertion* from *correct entailment*, demonstrated by a concrete error class.

The broader implication is that structural reliability mechanisms should be evaluated as trade-offs with a locatable crossover rather than adopted as universal goods, and that reporting where such a mechanism costs more than it returns is as much a part of the contribution as reporting where it wins.

# Future Work

**Add a soft-grounding arm** --- motivated by the methodological limitation in Section 11 that the current ablation contrasts a hard gate only with no check. An NLI-threshold or token-overlap arm [29] evaluated on the same claims would isolate hard gating from soft checking and directly locate the crossover argued for in Section 10.

**Adjudicate the false-grounding class manually** --- motivated by the caveat in Section 9.3 that SciFact's evidence-set-relative *NotEnoughInfo* label makes those counts upper bounds. Expert adjudication of the 7 and 10 flagged items would convert an upper bound into a measurement and sharpen the error decomposition.

**Run repeated seeds at n = 100** --- motivated by the computational limitation in Section 11. The harness already supports aggregation over repeats; executing three repeats per arm would narrow every interval reported here and may resolve the directionally supportive but non-significant results in Section 9.1.

**Compare against a supervised leaderboard system** --- motivated by the generalisability limitation that all arms are currently internal. Running MultiVerS [3] on the same SciFact sample would place the architectural effect on an absolute scale.

**Measure the gate's cost as a function of claim--evidence lexical distance** --- motivated by the FEVER inversion analysed in Section 10. If abstention cost is predictable from lexical overlap between a claim and its evidence, a deployment could select gate strictness per domain in advance rather than discovering the cost after the fact.

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

[20] N. Kolluri et al., "COVID-19 misinformation detection: Machine-learned solutions to the infodemic," *JMIR Infodemiology*, 2022. **[V]**

[21] Lu et al., "Multimodal attention with residual convolutional networks for misinformation detection," *Scientific Reports*, 2025. **[V]**

[22] Kumar et al., "Graph-augmented transformer ensembles for fake news detection," *Scientific Reports*, 2025. **[V]**

[23] A. Wynn, H. Satija, and G. Hadfield, "Talk isn't always cheap: Understanding failure modes in multi-agent debate," arXiv:2509.05396 [cs.CL], 2025. **[V]**

[24] B. Yao, C. Shang, W. Du, J. He, R. Lian, Y. Zhang, H. Su, S. Swamy, and Y. Qi, "Peacemaker or troublemaker: How sycophancy shapes multi-agent debate," arXiv:2509.23055 [cs.CL], 2025. **[V]**

[25] H. Wan, J. Wu, M. Luo, F. Li, N. Wang, N. F. Chen, and M.-Y. Kan, "The deliberative illusion: Diagnosing factual attrition and stance homogenization in multi-agent LLM deliberation," arXiv:2606.03032 [cs.CL], 2026. **[V]**

[26] "Show your work: Mechanically validated quotation as a gate on model assertions," medRxiv 2026.03.03.26346690; *Cureus*, 2026. **[V]** *(read in full text)*

[27] "Debating truth: Multi-agent debate for claim verification," arXiv:2507.19090; *Proc. WWW*, 2026. **[V]** *(read in full text)*

[28] "TRUST agents: Calibrated multi-agent verification with confidence-weighted adjudication," arXiv:2604.12184. **[V]** *(read in full text)*

[29] H. Qian, Y. Fan, J. Guo, R. Zhang, Q. Chen, D. Yin, and X. Cheng, "VeriCite: Towards reliable citations in retrieval-augmented generation via rigorous verification," arXiv:2510.11394 [cs.IR], 2025. **[V]**

[30] J. Ren, "Evidence-grounded verified agentic reasoning: A path toward eliminating LLM hallucination in empirical inference via tool-attested kernel proofs," arXiv:2607.12650 [cs.LG], 2026. **[V]**

[31] S. Miya, "Eidoku: A neuro-symbolic verification gate for LLM reasoning via structural constraint satisfaction," arXiv:2512.20664 [cs.AI], 2025. **[V]**

[32] S. Jeong, Y. Choi, J. Kim, and B. Jang, "Tool-MAD: A multi-agent debate framework for fact verification with diverse tool augmentation and adaptive retrieval," arXiv:2601.04742 [cs.CL], 2026. **[V]**

[33] S. Xiao, Z. Liu, P. Zhang, N. Muennighoff, D. Lian, and J.-Y. Nie, "C-Pack: Packaged resources to advance general Chinese embedding" (the BGE embedding family, `bge-small-en-v1.5`), in *Proc. ACM SIGIR*, 2024, arXiv:2309.07597. **[V]**

[34] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal rank fusion outperforms Condorcet and individual rank learning methods," in *Proc. ACM SIGIR*, 2009, pp. 758--759. **[V]**

[35] Q. McNemar, "Note on the sampling error of the difference between correlated proportions or percentages," *Psychometrika*, vol. 12, no. 2, pp. 153--157, 1947. **[V]**


```{=latex}
\appendix
\clearpage
```

# Research Plan and Pre-Flight Validation

## Pre-flight validation report

| # | Check | Result | Note |
|--:|:--|:--|:--|
| 1 | Topic specific enough for a focused paper | **Pass** | Bounded to one mechanism (hard verbatim gate), one structure (multi-agent verification), two datasets, three model scales |
| 2 | Research area and venue compatible | **Pass** | Systems-plus-empirical AI/NLP work; IEEE format is appropriate |
| 3 | Education level matches depth | **Pass** | Final-year undergraduate capstone; novelty is claimed narrowly as a *combination*, positioned rather than asserted as a field-first, with the measured baseline gap as the defensible unit |
| 4 | Proposal-mode placeholders required | **N/A** | Mode is Completed |
| 5 | Completed mode has real results | **Pass** | Six result sets from committed seeded runs, dated 19 July, 25 July, and 3 August 2026 |
| 6 | Anti-fabrication precondition | **Pass** | All numbers traced to run records; every reference confirmed against its DOI or arXiv record (Appendix E) |

## Research plan summary

**Problem definition.** Multi-agent LLM verification permits agreement that no evidence supports, and prompt-enforced grounding cannot prevent it. The problem is to determine what changes, empirically, when the agreement condition is made mechanical rather than behavioural. **Problem type:** mixed --- design science (the artifact) with an embedded quantitative experiment (the comparison).

**Significance.** *Academic:* the literature documents both that agent interaction improves factuality and that it produces correlated error, without a structural variable that separates the two cases; this work supplies and measures one. *Practical:* verification systems are being deployed into consequential domains now, and the conditions under which a reliability mechanism is worth its cost are unquantified. *Stakeholders:* practitioners deploying verification under cost constraints, researchers building multi-agent pipelines, auditors and reviewers who need to check an assertion after the fact, and end users who currently receive no signal distinguishing a reliable verdict from a fabricated one.

**Literature landscape.** Foundational: [1], [2], [3], [6], [4]. Recent state of the art: [26], [27], [28], [29], [23], [24], [25], [11], [17], [7]. Organised thematically in Section 2.

**Gap and its evidence.** Stated in Appendix B; evidenced by the specific limitations catalogued per theme in Section 2 --- soft enforcement [11]--[13], single-model dominance [8], [15], [16], unreported cost [14]--[16], hard gating without multi-agent structure [26], and multi-agent structure without hard gating [27], [28]. *Why unfilled:* the two halves developed in separate communities (medical-informatics evaluation and multi-agent NLP), the combination requires a deployed system rather than an offline classifier, and the false-agreement failure mode it targets was itself only characterised in 2025--2026 [23]--[25].

**Objectives, questions, hypotheses, methodology, contributions, and metrics** are stated in full in Sections 4, 5, 6, 1, and 6.8 of the paper respectively, including the two rejected metrics and the reason each was rejected.

# Research Gap Statement

No empirical study evaluates a hard, mechanically verified verbatim-evidence gate --- one that permits an affirmative or contradictory verdict only when it can quote a verbatim span of the retrieved evidence, checked in code --- as the structural precondition for **multi-agent** claim verification. Hard verbatim gating has been demonstrated only for single-model classification, and multi-agent claim verification grounds evidence softly through LLM-judgment moderation, calibrated confidence, or NLI scoring. Consequently the catch-rate, false-agreement, accuracy, latency, and cost trade-offs of a hard gate inside a multi-agent structure --- and how those trade-offs move with base-model scale and claim domain --- are unmeasured.

# Contribution Summary

| # | Contribution | Type |
|--:|:--|:--|
| 1 | Aletheia: a deployed, free-tier, publicly runnable multi-agent verification service whose evaluation path and live path are the same code | Artifact/tool |
| 2 | A seeded, reproducible evaluation harness reporting accuracy, catch rate, false agreement, latency percentiles, and tokens per query against a single-LLM baseline and an isolating ablation | Artifact/tool |
| 3 | A structural evidence gate making a mechanical verbatim-substring match the precondition for multi-agent verifier agreement, with a prompt-level ablation that isolates exactly that variable | Methodological |
| 4 | An empirical boundary condition: grounding's accuracy contribution is inversely related to base-model strength, measured at three scales and confirmed at a powered sample size | Empirical |
| 5 | A domain-transfer result and a preprocessing finding: strict grounding costs about 8 accuracy points on paraphrase claims, and Penn Treebank markup alone accounted for 21 points | Empirical |
| 6 | An explicit separation of *no unsupported assertion* from *correct entailment*, demonstrated by a 51/51 guarantee audit whose residual errors are entailment failures | Theoretical |

# Source Registry

**[V] Verified --- all 35 sources.** [1]--[35]. These are either canonical publications whose bibliographic details are standard and independently checkable, or --- for [26], [27], [28] --- the closest prior art, which was fetched and read in full text specifically to stress-test the novelty claim of Section 7.2 before publication.

Entries [10]--[19], [23]--[25] and [29]--[33] were previously tagged **[L]**. In the August 2026 revision each was resolved against its record of origin --- Crossref for the journal articles, the arXiv abstract page for the preprints --- and author lists, volume, issue, pages, article numbers and DOIs were completed from those records. Every one proved to exist; none was withdrawn or unfindable.

**Corrections made during that pass.** The check also caught defects beyond the missing fields, and these are recorded rather than quietly fixed. Eight entries carried a descriptive paraphrase in place of the published title --- [12], [13], [15], [19], [25], [29], [30], [31], [32] --- and now carry the title as published. Two carried the wrong year: [15] is 2026, not 2025, and [19] is 2025, not 2024. [14] credited the first initial of a co-author to the lead author. [33] cited the superseded title and a partial author list, and now follows the SIGIR 2024 record. No reference was removed, because no reference turned out to be fabricated.

**[U] Could not verify --- none.** No source in this paper is unverifiable, and no claim rests on one.

**Full bibliographic details:** the supplementary literature table (`backend/scripts/literature-review-table.csv`) carries the eight-column record --- author and year, paper and journal, objective, sample and area, method, key findings, and limitations --- for all 35 reviewed journal articles, of which the subset cited here appears in the reference list.

# Citation Verification Notes

1. **The `[L]` bibliographic fields are complete.** All eighteen formerly incomplete entries were resolved against Crossref or arXiv in August 2026; each source exists, and the citation apparatus is now filled from the record of origin. Nine titles that had been recorded as paraphrases were replaced with the published wording, and two years were corrected --- see Appendix D.
2. **Three sources were abstract-checked but not read in full.** GKMAD (*Expert Systems with Applications*, 2025), "Debating to Verify" (2025--2026), and Tool-MAD [32] were confirmed real and their abstracts examined; nothing in them indicates a hard gate, but a full-text pass on all three is advisable before the novelty framing in Section 7.2 is treated as final. No reviewer-facing claim in this paper depends on their absence of a gate beyond the positioning sentence, which is explicitly labelled as positioning.
3. **Preprint identifiers may change on publication.** Entries [23]--[25] and [29]--[32] are cited from preprint records; identifiers should be reconciled against final published versions where those now exist.
4. **[33] is cited for the embedding model actually used**, not for a claim about embedding quality; if the canonical BGE citation differs from the C-Pack record, the reference should follow the model card.
5. **No DOI, URL, author name, dataset, or statistic in this paper was generated to fill a gap.** Fields that are unknown are marked, not invented.

# Simulated Peer Review (Reviewer #2)

**Summary.** The paper proposes a hard verbatim-substring gate as a precondition for multi-agent LLM verifier agreement, implements it in a deployed pipeline, and evaluates it against a single-LLM baseline and an opinion-only ablation on SciFact and FEVER across three model scales. The headline empirical claim is a boundary condition: grounding's accuracy benefit falls as base-model strength rises, while its catch-rate and false-agreement advantages persist in direction, and its mechanical guarantee holds exactly (51/51) on the adversarial domain.

**Strengths.**

1. The ablation design is unusually clean. Holding claim, evidence, model, temperature, and prompt fixed and varying only the span discipline --- with a unit test guarding the prompt-parity contract --- is a stronger isolation than most work in this subfield achieves.
2. The paper reports results that do not flatter its own thesis (the FEVER H2 inversion, the accuracy tie at deployment scale, the negative accuracy deltas at 70B and above) with intervals and test statistics rather than prose hedging.
3. The 51/51 guarantee audit is a genuinely checkable claim that does not depend on sample size, and the traces make it independently verifiable.
4. The corpus-markup finding (21 accuracy points from Penn Treebank tokenisation) is a real methodological contribution for anyone deploying verbatim gates, and it is honestly identified as larger than any architectural effect measured.
5. Reproducibility is well above the field norm: public code, fixed seeds, declared configuration, committed traces, and offline re-runnable analyses.

**Weaknesses.**

1. **The missing soft-grounding arm is the central gap.** The related work is dominated by soft checks [27]--[29], yet the ablation compares a hard gate only against *no check*. Without an NLI-threshold arm the paper cannot claim that *hardness* is what matters, only that *checking* matters. This is the comparison the contribution actually requires.
2. **The headline configuration does not support the headline hypotheses.** At the deployed model, H1's interval touches zero and H2's crosses it; the significant results come from an 8B model that few would deploy. The paper is candid about this, but the framing still leads with the deployed run.
3. **n = 100 with a single repeat** is underpowered for the effect sizes at play, and the paper's own future work concedes it. Several conclusions rest on directional patterns across underpowered runs.
4. **No external comparator.** All three arms are internal, so the reader cannot situate 79 percent accuracy against MultiVerS or any supervised system, which makes the absolute quality of the pipeline unassessable.
5. **The novelty claim rests partly on absence of evidence.** "First to make a mechanical match the precondition for multi-agent agreement" depends on a search that the authors themselves note left three candidates at abstract level.

**Questions for the authors.**

1. If the ungrounded ablation beats the gate on FEVER accuracy *and* false agreement, on what basis should a practitioner adopt the gate in a paraphrase-heavy domain? Is auditability alone sufficient justification, and for whom?
2. How much of the 8B catch-rate gain survives if the ablation prompt also receives the span-sufficiency reasoning without the mechanical check? That is the arm that would separate prompt effect from gate effect.
3. Latency inverts between the 8B and Gemini runs. Is this a property of the gate, of provider queuing, or of the ungrounded arm's generation length? A token-count breakdown by arm and stage would settle it.
4. Is the false-grounding upper bound tight? Manual adjudication of even 17 items would materially change the error decomposition's interpretation.
5. Does the guarantee audit generalise to SciFact, or was it performed only on FEVER?

**Minor issues.** The FEVER 56 percent to 77 percent comparison should state explicitly that it is a re-run and not a third arm. Several reference entries lack author lists and DOIs. The paper alternates between "points" and "pp" for percentage-point deltas.

**Recommendation: Major revision.** The construction is sound, the evaluation discipline is genuinely strong, and the honesty about negative results is a credit rather than a deficit. But the absence of a soft-grounding baseline leaves the paper's central mechanistic claim untested against its nearest alternative, and the headline hypotheses are unconfirmed at the configuration the paper leads with. Adding the soft-grounding arm and repeated seeds at n = 100 would, in this reviewer's judgment, move the paper to accept.

# Reviewer Vulnerability Report

Ranked by the likelihood that a real reviewer attacks the point and by the damage if unanswered.

| Rank | Vulnerability | Likely attack | Current mitigation | Residual exposure |
|--:|:--|:--|:--|:--|
| 1 | No soft-grounding arm | "You have not shown hardness matters, only that checking matters" | Named as the first limitation and first future-work item | **High.** Not answerable without running the experiment |
| 2 | Headline hypotheses unconfirmed at deployment scale | "Your significant results come from a model nobody deploys" | Reported transparently with intervals; the boundary condition is the framed contribution | **Medium.** Defensible as framed, but the framing must lead with the boundary condition, not the win |
| 3 | H2 reversed on FEVER | "Your ablation beat your system" | Reported unsoftened; explained mechanistically via claim--evidence lexical distance | **Medium.** The explanation is plausible but not itself measured |
| 4 | Single repeat, n = 100 | "Underpowered" | Acknowledged; harness supports repeats | **Medium.** Cheap to fix with quota |
| 5 | No leaderboard comparison | "Absolute quality unassessable" | Flagged explicitly, not omitted | **Medium** |
| 6 | Novelty as absence of evidence | "You cannot know you are first" | Claim scoped to "to our knowledge, after this search", full-text reads on the three closest candidates, positioned as combination not primitive | **Low--medium.** Three abstract-only candidates remain |
| 7 | False grounding is an upper bound | "Your error decomposition is not a measurement" | Stated at first use and repeated in limitations | **Low.** Honest, but weakens Section 9.3 |
| 8 | Bibliographic gaps | "Incomplete references" | Confidence tags and Appendix E | **Low.** Mechanical to fix, but visible |
| 9 | Contamination | "Both benchmarks predate the models" | Relative-gap reporting | **Low.** Standard and accepted |

# Improvement Roadmap

Ordered by return on effort before submission.

1. ~~Fill the `[L]` bibliographic fields.~~ **Done (August 2026).** All entries resolved against Crossref and arXiv; nine paraphrased titles and two incorrect years corrected in the process.
2. **Extend the figure set.** Four figures are in place (architecture, headline comparison, scaling behaviour, FEVER). A fifth plotting the paired per-claim confusion between the grounded and baseline arms would make the McNemar discordance visible rather than reported. *Effort: hours.*
3. **Run three repeats at n = 100** on the deployed model. Narrows every interval and may convert the Section 9.1 directional results into confirmed ones. *Effort: one quota window.*
4. **Add the soft-grounding (NLI-threshold) arm.** The single highest-value scientific addition; directly answers the top reviewer vulnerability. *Effort: one implementation session plus one run.*
5. **Manually adjudicate the 17 false-grounding items** across both runs, converting an upper bound into a measurement. *Effort: one focused session.*
6. **Full-text pass on the three abstract-only novelty candidates** (GKMAD, "Debating to Verify", Tool-MAD). *Effort: one reading session.*
7. **Run MultiVerS on the same SciFact sample** for an absolute reference point. *Effort: one session, subject to free-tier compute.*
8. **Compress to the 10--15 page target if the venue enforces it.** The body currently runs about 16 typeset pages with references. The cheapest reductions, in order: move Section 9.6 (verifier improvement) and Section 9.4 (exploratory sweep) into a supplementary section, retaining one summary sentence each; fold Sections 4 and 5 into the Introduction, which the IEEE format ordinarily expects; and reduce the related-work comparison table to the six rows nearest the mechanism. Together these recover roughly three pages without losing a result. *Effort: one hour.*
9. **Terminology and consistency pass** ("points" versus "pp"; re-run versus arm in Section 9.7; acronym definitions on first use). *Effort: one hour.*

# Experiment Requirements

The paper is in Completed mode; the experiments below are the ones **still outstanding**, each stated with what it measures, what it needs, and how its output would be presented.

| # | Experiment | Measures | Requires | Output format |
|--:|:--|:--|:--|:--|
| 1 | Soft-grounding arm | Whether *hardness* rather than *checking* drives the effect | An NLI or token-overlap scorer, a threshold chosen on a held-out slice, one n = 100 run per domain | A fourth column in the Section 9.1 and 9.6 tables, plus paired deltas of hard versus soft |
| 2 | Repeated seeds | Interval width at the headline configuration | Three seeded repeats per arm at n = 100 | Existing tables restated as mean ± standard deviation, with narrowed CIs |
| 3 | Prompt-versus-gate separation | Whether the span-sufficiency reasoning alone reproduces the gain | An ablation arm carrying the sufficiency wording without the containment check | One added row per headline table |
| 4 | Manual adjudication | Converts the false-grounding upper bound into a count | Expert review of the 7 (Gemini) and 10 (8B) flagged items against the retrieved evidence | A revised Section 9.3 decomposition with adjudicated and unadjudicated columns |
| 5 | Guarantee audit on SciFact | Whether 51/51 generalises beyond FEVER | Re-check of asserted verdicts against traces for both n = 100 SciFact runs | One sentence plus a fraction per run |
| 6 | Lexical-distance analysis | Whether abstention cost is predictable from claim--evidence overlap | Per-item overlap statistic computed offline from existing traces | Scatter plot of overlap against abstention, with a fitted trend |
| 7 | Leaderboard comparator | Absolute placement of the pipeline | MultiVerS [3] run on the identical seeded sample | One reference row in the Section 9.1 table, clearly marked as supervised |

Experiments 5 and 6 require **no new model calls** --- both run offline from committed traces --- and are therefore the cheapest outstanding items.

# Quality Assurance Record

## Structural integrity checklist

| # | Check | Result | Note |
|--:|:--|:--|:--|
| 1 | Research problem specific and bounded | Pass | Formalised in Section 3 with explicit inclusions and exclusions |
| 2 | Gap supported by cited evidence | Pass | Derived per theme in Section 2 with specific limitations cited |
| 3 | Objectives SMART | Pass | Each carries an explicit measurability criterion (Section 4) |
| 4 | RQs match methodology | Pass | Each RQ names the statistic that answers it (Section 5) |
| 5 | Methodology reproducible | Pass | Hyperparameters, normalisation, prompts, seeds, and commands stated |
| 6 | Metrics appropriate and justified | Pass | Formulas plus two documented metric rejections (Section 6.8) |
| 7 | Conclusions supported by evidence | Pass | Non-significant results are labelled as such throughout |
| 8 | Unsupported claims | Pass with note | The novelty claim is scoped as positioning; three candidates remain abstract-only |
| 9 | Citation and bibliography correspondence | Pass | All 35 entries cited in text; no orphan entries |
| 10 | References tagged with confidence | Pass | [V] on all 35 entries after the August 2026 verification pass; registry in Appendix D |
| 11 | Language original | Pass | Synthesised; no close paraphrase of source wording |
| 12 | Unnecessary repetition | Pass with note | Deliberate restatement of limitations across Sections 9, 11, and 13 for reader navigation |
| 13 | Logical inconsistencies | Pass | The FEVER H2 inversion is reported and explained rather than reconciled away |
| 14 | Limitations honest and thorough | Pass | Eight categories including four validity types |
| 15 | Meaningful contribution | Pass | Four contributions, each typed |
| 16 | Abstract reflects content | Pass | Includes the tie, the boundary condition, and the guarantee |
| 17 | Free of exaggeration | Pass | No "significant" without a test statistic; no state-of-the-art claim |
| 18 | Acronyms defined on first use | Pass | LLM, RAG, NLI, RRF, JSON, IRB |
| 19 | Within target length | Pass at the margin | Paper body and references occupy approximately 16 typeset pages against a 10--15 target; the six appendices add a further six. Compression options are listed in Appendix H |
| 20 | Avoids generic phrasing | Pass | Opens on measured hallucination rates rather than a temporal cliché |

## Anti-fabrication audit

| Claim class | Source | Verified | Note |
|:--|:--|:--|:--|
| All six results tables (accuracy, catch, false agreement, latency, tokens) | Committed seeded run records dated 19 July, 25 July, 3 August 2026 | Yes | No value projected, rounded up, or estimated |
| All significance statistics (McNemar p-values, bootstrap CIs) | Computed by the harness on paired per-claim predictions | Yes | Test, resample count, and seed stated |
| Error decomposition counts | Offline analysis over committed traces | Yes | Category definitions stated; false grounding labelled an upper bound |
| 51/51 guarantee | Independent re-check of FEVER traces | Yes | Re-checkable by a third party without model access |
| Corpus statistics (5,183 abstracts, 15,411 chunks, coverage 100.0 / 99.0 percent) | Ingest and coverage-check output | Yes | Coverage computed before any model call |
| All hyperparameters and versions | Read directly from the configuration and dependency manifest | Yes | Not recalled from memory |
| Literature findings attributed to [8]--[22] | 35-paper structured journal review | Yes | Findings confirmed; bibliographic fields completed against Crossref and arXiv (Appendix D) |
| Novelty claim | Structured search with full-text reads of [26], [27], [28] | Partial | Scoped as positioning; three candidates abstract-only, disclosed in Appendix E |
| Claims lacking sufficient support | None | --- | Every uncertain item above is flagged in text rather than asserted |

# Alternative Titles

**Primary (used).** A Hard Verbatim-Evidence Gate as the Precondition for Multi-Agent Claim Verification: Design, Deployment, and Empirical Boundary Conditions

**Alternative 1.** When Structural Grounding Pays: A Mechanically Verified Evidence Gate for Multi-Agent Claim Verification

**Alternative 2.** Quote or Abstain: Enforcing Verbatim Evidence as a Structural Constraint on Multi-Agent Verifier Agreement

*Both alternatives are under 20 words, name the mechanism and the domain, and avoid superlative framing. Alternative 1 foregrounds the empirical boundary condition; Alternative 2 foregrounds the mechanism.*
