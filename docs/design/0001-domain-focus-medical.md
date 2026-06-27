# ADR 0001 — Medical domain first, on a domain-agnostic engine

- **Status:** Accepted (locked)
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

Aletheia's thesis — evidence-grounded verification that surfaces disagreement — is
itself domain-independent. But a verification system is only as credible as the corpus
it grounds in, and a corpus is only authoritative *within* a domain. Two failure modes
bound the decision:

- Trying to be authoritative everywhere at once would dilute the corpus, blur the trust
  model, and weaken the headline evaluation. `ANTI_DRIFT.md` already forbids this: "Do
  **not** expand to many domains … breadth dilutes the measurable result."
- Hard-coding a single domain *into the engine* would betray the thesis and throw away
  generality the architecture already has.

## Decision

Aletheia is built **medical-first** on a **domain-agnostic engine.**

- **Medical-first.** The curated corpus, the trust tiers, the benchmark sets, and the
  worked examples all target the medical domain (see [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)
  for the corpus itself).
- **Domain-agnostic engine.** The corpus and the **source connectors** that populate it
  are *pluggable*. A connector knows how to fetch and normalize sources for one domain
  and tag them with a trust tier; the Generator → Retriever → Verifier → Aggregator
  pipeline knows nothing about medicine specifically. Adding a domain means adding a
  connector and a corpus — not changing the core.
- **Other domains are roadmap, not scope.** Scientific and legal domains are added
  *later*, as new connectors over the same engine, and only once the medical path is
  solid end to end.

## Consequences

- Medical sources, medical benchmarks, and medical examples are the focus through the
  paper. There is no present multi-domain surface area to build, maintain, or evaluate.
- The retrieval/grounding layer is designed around a **connector interface** and a
  **domain-tagged corpus** from day one, so "medical" is data and configuration rather
  than branching logic in the engine.
- A clean future-extension story (science, law) exists for reviewers without diluting
  the current measurable result — consistent with `ANTI_DRIFT.md`'s "keep the corpus and
  benchmarks focused."

## Related

- [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) — what the medical corpus is.
- `PROJECT_CHARTER.md` §6 (scope), `ANTI_DRIFT.md` (out of scope: many domains).
