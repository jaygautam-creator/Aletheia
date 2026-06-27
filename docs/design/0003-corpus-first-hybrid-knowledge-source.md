# ADR 0003 — Corpus-first knowledge, with a clearly-marked lower-trust live fallback

- **Status:** Accepted (locked)
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

Verification quality is bounded by what the Retriever can ground in (`EVALUATION.md`
§7, "retriever ceiling"). Two extremes bound the design:

- A corpus that is too small leaves legitimate claims `Unverifiable` for lack of
  evidence.
- An open live-web source injects low-trust material that would undermine the grounding
  guarantee if mixed in as though it were authoritative.

Neither extreme is acceptable, and **trust must be legible per piece of evidence** — not
assumed uniform across sources.

## Decision

Knowledge is **hybrid and corpus-first.**

1. **High-trust foundation — a curated corpus.** Built from *free, authoritative*
   medical literature: **PubMed** and **PubMed Central (PMC) open-access**. This is the
   default, high-trust evidence source and the substrate for all benchmarking
   ([ADR-0006](0006-benchmark-on-fixed-corpus.md)).
2. **Lower-trust live fallback.** When the corpus lacks sufficient evidence for a claim,
   the system *may* fall back to live literature/web search — surfaced as a
   **clearly-marked, lower-trust evidence tier**, never silently mixed in as if it were
   corpus-grade.
3. **A trust tier on every piece of evidence.** Every evidence span carries a source
   **trust tier** end to end — through retrieval, the verdict, aggregation, the explained
   confidence ([ADR-0005](0005-confidence-from-evidence.md)), and the disagreement
   weighting ([ADR-0004](0004-surface-disagreement.md)). There is no untiered evidence.

**Sequencing is strict: corpus-first, fallback later.** The corpus path is built and
proven solid *before* the live fallback is started. **Never both at once.** The fallback
is a later step layered onto a working corpus, not a parallel track.

## Consequences

- The pgvector schema models a **trust tier as a first-class field** on sources/chunks
  from the very first migration.
- **Phase 2 implements only the corpus path** (ingestion → hybrid retrieval →
  grounding). The live fallback is explicitly *out* of Phase 2's initial scope and is
  added once corpus retrieval is solid.
- Benchmarks run on the fixed corpus ([ADR-0006](0006-benchmark-on-fixed-corpus.md)); the
  live fallback is a *demonstrated* capability, not a benchmarked component.
- PubMed/PMC open-access keeps the corpus **free and redistributable/scriptable to
  download**, consistent with the free-tier non-negotiable.

## Related

- [ADR-0006](0006-benchmark-on-fixed-corpus.md) (benchmark on the fixed corpus),
  [ADR-0004](0004-surface-disagreement.md), [ADR-0005](0005-confidence-from-evidence.md).
