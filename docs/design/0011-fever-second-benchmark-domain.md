# ADR 0011 — FEVER as a second benchmark domain, on a scoped corpus slice

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decided:** Workstream E (author-requested generalization, [plan 0002](../plans/0002-generalization-plan.md))
- **Deciders:** Jay Gautam

## Context

[ADR-0010](0010-own-document-verification-any-domain.md) made the *product*
any-domain: a caller who supplies evidence can verify a claim about anything.
It explicitly left the *measured* generalization story open — every benchmark
number so far is SciFact, a single medical dataset, so "the grounding
advantage isn't a SciFact artifact" is still an untested claim.

FEVER (Thorne et al., *FEVER: a Large-scale Dataset for Fact Extraction and
VERification*, NAACL 2018) is a natural second domain: 145K claims about
Wikipedia facts spanning history, sport, politics, and culture, labelled
`SUPPORTS` / `REFUTES` / `NOT ENOUGH INFO` — a clean map onto the pipeline's
own `Verdict` space. But its evidence source is the full Wikipedia dump
(~5.4M pages), which is not free-tier-ingestable, and
[ADR-0006](0006-benchmark-on-fixed-corpus.md) already locked "benchmark on a
fixed corpus" as the shape of every headline number this project reports.

## Decision

**Build a seeded, closed corpus slice sized like SciFact's (~5K documents),
not the full Wikipedia dump.** The slice is deterministic given a claims file,
a sample size, and a seed: every Wikipedia page cited by the sampled claims'
gold evidence, plus seeded random distractor pages up to the target size. This
keeps FEVER inside every ground rule already in force:

- **Corpus-first, not open retrieval** ([ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)):
  the corpus is ingested and frozen before any run, exactly like SciFact.
- **Benchmark on a fixed corpus** ([ADR-0006](0006-benchmark-on-fixed-corpus.md)):
  the slice is the "fixed corpus" for FEVER's run; nothing is fetched live.
- **Free-tier only, additive verdict contract, offline-testable connector**:
  unchanged from every prior ADR in this project.

**Honest limitation, stated here and repeated in `EVALUATION.md`:** retrieval
against a ~5K-document slice built from the *sampled claims' own* evidence
pages is easier than retrieval against the full 5.4M-page Wikipedia dump used
by the FEVER shared task. FEVER numbers reported here are **not** comparable
to FEVER leaderboard systems. That is consistent with ADR-0006's research
question — grounded-vs-baseline on a fixed corpus — not a claim about
open-domain retrieval at Wikipedia scale.

## Consequences

- A new corpus connector (`corpus/connectors/fever.py`) and a new benchmark
  loader (`evaluation/benchmark.py`'s FEVER claim parser) exist alongside the
  SciFact ones, sharing the same `BenchmarkItem` shape and `stratified_sample`
  machinery — no new abstraction, one more instance of the existing one.
- `phase3.py` gains a `--dataset {scifact,fever}` flag. The SciFact §6.2
  headline table and its markers in `EVALUATION.md` are untouched; FEVER
  results render in a new, clearly separate "Generalization to a second
  domain" section with their own markers.
- The frontend benchmark-results JSON grows a `domain` field, read
  defensively (a missing field means `scifact`), so the existing SciFact card
  never breaks when the FEVER card is added.
- The corpus-slice builder (`--sample`/`--seed`) is pure and unit-tested
  offline; only the eventual live FEVER run (E4) spends Groq quota, on its own
  session, exactly like the SciFact re-validation.
- FEVER data files (dumps, claims) are gitignored under `backend/data/fever/`,
  same as SciFact — the dataset itself is never redistributed, only the
  connector and slice-builder code that reads it.
