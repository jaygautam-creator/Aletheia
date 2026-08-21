---
title: "Research Gap Identification --- Literature Review Dossier"
subtitle: "Evidence-grounded reduction of hallucination in LLM verification systems"
author: "Jay Gautam"
date: "August 2026"
geometry: "a4paper, landscape, margin=1.4cm"
fontsize: 9pt
---

## 1. Final Research Topic

**Evidence-grounded reduction of hallucination in large-language-model verification systems: from soft factuality checks to a structurally-verified, multi-agent claim-checking gate.**

Focused on: (a) *problem* --- hallucination / unsupported assertions in LLM output; (b) *mechanism* --- evidence grounding, from soft prompt-based grounding to a hard, mechanically-verified evidence gate; (c) *setting* --- automated claim/fact verification. This is the literature space of the Aletheia system.

## 2. Keywords

large language models; hallucination detection; hallucination mitigation; retrieval-augmented generation; evidence grounding; factual consistency; automated claim / fact verification; multi-agent LLM systems; faithfulness; misinformation detection

## 3. Literature Review Table (35 original empirical journal articles)

*Reviews, systematic reviews, meta-analyses, and conference/proceedings papers deliberately excluded. Rows marked (R) were read from source; rows marked (C) are real journal articles whose author/details you must confirm from the DOI.*

| # | Author & Year | Paper / Journal | Objective | Sample / Area | Method | Key Findings | Limitations |
|--|--|--|--|--|--|--|--|
| 1 | Massenon 2025 (R) | LLM hallucinations in app reviews / Sci. Reports | Taxonomy of real LLM hallucinations | 3M reviews, 90 apps | NMF + VADER + manual annot. | Factual errors 38% of reports | English-only reviews |
| 2 | Chelli 2024 (C) | Hallucination rates of ChatGPT/Bard / JMIR | Measure hallucinated references | Rotator-cuff review refs | Comparative ref. analysis | Many hallucinated references | Single clinical topic |
| 3 | npj Dig. Med. 2025 (C) | Clinical-safety hallucination framework / npj Dig. Med. | Quantify safety risk of LLM summaries | 12,999 clinician sentences | Clinician-annotation framework | 1.47% hallucination, 3.45% omission | Summarisation only |
| 4 | NEJM AI 2025 (C) | Verify facts in LLM clinical notes via EHR / NEJM AI | Verify LLM text against records | Care docs + EHR | Fact-check vs EHR | Detectable factual errors | Single-site EHR |
| 5 | Yanagita 2023 (R) | ChatGPT on Japanese medical exam / JMIR Form. Res. | LLM factual accuracy, non-English | 292 NMLE questions | GPT-3.5 vs GPT-4 + physicians | GPT-4 81.5% vs 42.8% | Excluded image questions |
| 6 | Comput. Biol. Med. 2024 (C) | GPT-4 vs Gemini references / Comput. Biol. Med. | Compare citation credibility | Medical research refs | Paired t-tests | Differences in ref. reliability | Citations only |
| 7 | Khatri 2025 (C) | ChatGPT drug-info accuracy / JACCP | Accuracy + reproducibility | Drug-info questions | Expert eval of repeats | Variable accuracy/reproducibility | Single domain |
| 8 | Krishnamurthy 2024 (C) | Credibility framework for fact-checking / IEEE Access | Add credibility layer to LLM checking | Claim sets | LLM + credibility scoring | Credibility signals help | Framework; limited eval |
| 9 | npj Dig. Med. 2025 (C) | RAG for 10 LLMs, medical fitness / npj Dig. Med. | Does RAG generalize across LLMs | 10 LLMs, fitness assess. | RAG over guidelines | GPT-4+RAG 96.4%, no hallucination | Single domain |
| 10 | npj Dig. Med. 2025 (C) | Long-context RAG for medical QA / npj Dig. Med. | Long-context grounded QA | Medical QA | Long-context RAG | Longer context improves faithfulness | Medical only |
| 11 | npj Dig. Med. 2025 (C) | RAG for local LLM in radiology / npj Dig. Med. | Improve small-LLM factuality | Radiology queries | RAG over guidelines | RAG lifts local-LLM accuracy | Single specialty |
| 12 | JMIR 2025 (C) | Two-layer RAG, low-resource medical QA / JMIR | Grounded QA with scarce corpora | Reddit medical Q&A | Two-layer RAG | Improves low-resource grounding | Proof-of-concept |
| 13 | J. Intell. Inf. Syst. 2026 (C) | Multimodal misinfo via RAG+LLM / JIIS | Cross-language RAG detection | Multilingual multimodal | RAG + LLM verifier | RAG improves cross-lingual detection | Evidence quality varies |
| 14 | ESWA 2024 (C) | Factual-consistency eval in LLM era / ESWA | Better factual-consistency metric | Summ. factuality sets | LLM-based metric | Better human correlation | Summarisation only |
| 15 | ESWA 2025 (C) | Multi-agent collaborative filtering / ESWA | Reduce reasoning hallucination | Reasoning/QA sets | Multi-agent + filtering | Cross-checking lowers hallucination | Compute-heavy; not gated |
| 16 | Martin 2022 (C) | FacTeR-Check (similarity + NLI) / Knowl.-Based Syst. | Evidence retrieval + verification | COVID Spanish claims | Similarity retrieval + NLI | Evidence-linked verification | Spanish/COVID; not generative |
| 17 | IPM 2025 (C) | Misinfo detection via pretrained LMs / IPM | Thematic+sentiment+stance cues | US-election tweets | RoBERTa/BERT/GPT PLMs | PLMs dominate; strong F1 | English; content-only |
| 18 | Eronen 2023 (C) | Cross-lingual transfer selection / IPM | Best source language, zero-shot | Language pairs | XLM-R + similarity | Similarity selection lifts transfer | No evidence/explanation |
| 19 | Skrlj 2022 (C) | KG-informed fake-news classification / Neurocomputing | Use KG knowledge | Fake-news corpora | Heterog. ensembles + KG | KG features add robustness | KG-coverage dependent |
| 20 | Kolluri 2022 (R) | COVID misinfo ML solutions / JMIR Infodemiology | Scale beyond human checkers | ~38k articles + crowd | ML/DL + human blend | 96.55% ML; 99.1% blended | Crowd on one set |
| 21 | Lu 2025 (R) | Multimodal attention + residual CNN / Sci. Reports | Text/image/video detection | LIAR/FakeNewsNet/Weibo | ResNet + attention fusion | 0.977 acc; beat GPT-3.5 | No category eval |
| 22 | Kumar 2025 (R) | Graph-augmented transformer ensemble / Sci. Reports | Accuracy + generalization | LIAR + FakeNewsNet | BERT + GNN + ensemble | 96.5% acc; +4.2% F1 | Heavy compute |
| 23 | Wang 2025 (R) | BERT-LSTM misinfo, mobile networks / Sci. Reports | Text-only detection | 39,940 tweets | BERT + LSTM | 93.51% acc | Single-modality |
| 24 | Sharma 2024 (R) | SEMTEC emotion/sentiment rumor / PeerJ CS | Emotion cues for rumor | PHEME + Twitter24 | BERT + BiLSTM + TextBlob | 92% on PHEME | Latency; weak real-time |
| 25 | Jadhav 2025 (R) | HEMT-Fake multilingual multimodal / Front. AI | Explainable, Indian languages | 74k Hindi/Guj/Mar/Tel/Eng | XLM-R + CNN-BiLSTM + SHAP | ~89% F1; +5% over XLM-R | Modest user validation |
| 26 | Feroz 2026 (R) | Urdu news with BERT+GloVe / Sci. Reports | Low-resource Urdu detection | 14,178 Urdu articles | XLM-R + BERT+GloVe | F1 0.956 | Text-only |
| 27 | Almandouh 2024 (R) | Ensemble DL Arabic fake news / Sci. Reports | Arabic detection | AFND + ARABICFAKETWEETS | FastText + BiLSTM+BiGRU | Up to 0.99 acc | Dialect variation |
| 28 | Merzah 2026 (R) | CNN-BiLSTM Arabic & English / Front. Big Data | One model, two languages | AFND+ANS+WELFake | CNN + dual BiLSTM | 94.4% / 98.9% | Satire; two languages |
| 29 | Al-alshaqi 2024 (R) | Ensemble multimodal fake news / Sensors | Text+image+video | ISOT + MediaEval2016 | ML + BERT + CNN | RF 99%; +3.1% multimodal | Not global dataset |
| 30 | Alarfaj 2025 (R) | RoBERTa-Large clickbait + XAI / Sci. Reports | Explainable clickbait | 32,000 headlines | RoBERTa-Large + LIME/SHAP | 97% acc | English-only |
| 31 | Muqadas 2025 (R) | Sentence-embedding clickbait / Sci. Reports | Low-resource Urdu clickbait | 1,000 Urdu headlines | ML + LSTM/Bi-LSTM | 88% acc | No transformer |
| 32 | Mathematics 2025 (C) | ML vs DL empirical comparison / Mathematics | Benchmark models | Public benchmarks | Comparative; ALBERT | Transformers SOTA | English text |
| 33 | Mathematics 2026 (C) | Multimodal ensemble text+image / Mathematics | Fuse text+image | Public multimodal | ViLBERT + ensemble | Ensemble beats unimodal | No evidence/explanation |
| 34 | Appl. Intell. 2022 (C) | Rumor detection via GNNs / Applied Intelligence | Propagation structure | Twitter/Weibo graphs | Hierarchical GNN | Aggregation improves detection | Needs propagation graphs |
| 35 | Neural Comput. Appl. 2025 (C) | Multi-modal domain adaptation / NCAA | Reduce cross-event shift | Weibo + Twitter | BERT+EfficientNet+DA | Improves generalization | Needs event data |

## 4. Common Findings & Patterns

1. **Two framings, one blind spot** --- work splits into accuracy benchmarking and hallucination detection; almost none enforce a *guarantee* that every assertion is evidence-backed.
2. **Grounding is soft** --- RAG reduces hallucination (sometimes to ~0%) but grounding is prompt-enforced, never mechanically checked.
3. **Single-model dominance** --- multi-agent LLM reliability appears in journals only once or twice, and its false-agreement risk is unexamined.
4. **Cost unreported** --- accuracy/F1/hallucination-rate are reported, but rarely the latency and token cost of the reliability mechanism.
5. **Same benchmarks/domains** --- LIAR, FEVER, PHEME, Weibo, AFND, clinical guidelines recur; frozen-corpus reproducible benchmarking is rare.
6. **Language skew** --- English dominates; Indian-multilingual and low-resource settings remain thin.

## 5. Recurring Limitations & Future Scope

- Soft grounding can still be violated (prompting does not prevent contradiction/over-reach beyond retrieved text).
- No structural guarantee and no explanation --- verdicts are black-box labels not tied to a checkable evidence span.
- Multi-agent reliability barely studied; correlated-agreement risk under-measured.
- Latency/cost of the reliability mechanism almost never quantified.
- Domain- and language-bound; weak cross-domain/cross-lingual generalization.
- Little human-in-the-loop or deployed, end-to-end evaluation.

## 6. Research Gap Statement

Across the literature, LLM factual reliability is pursued either by measuring a single model's accuracy / hallucination rate, or by **softly** grounding generation in retrieved evidence through prompting --- approaches that *reduce*, but cannot *guarantee*, unsupported assertions, and that are almost never evaluated for their latency and cost. Multi-agent LLM verification, though promising, is scarcely studied in empirical journal work and carries an unexamined risk of **correlated agreement on wrong answers**. There is therefore a clear **methodological gap**: no empirical study evaluates a **hard, mechanically-verified evidence gate** --- one that permits an affirmative or contradictory verdict only when it can quote a verbatim span of retrieved evidence --- as the structural precondition for **multi-agent** claim verification, together with its catch-rate, false-agreement, accuracy, latency and cost trade-offs across model scales and domains.

*Gap type: primarily Methodological, with a secondary Variable gap (false-agreement and cost as under-measured outcomes). This aligns the identified gap with the Aletheia system, so the gap and the eventual paper share one subject.*
