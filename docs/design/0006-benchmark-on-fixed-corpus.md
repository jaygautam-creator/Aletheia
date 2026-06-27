# ADR 0006 — Benchmark on the fixed corpus; the live fallback is demonstrated, not benchmarked

- **Status:** Accepted (locked)
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

The paper's credibility rests on **reproducible** numbers (`EVALUATION.md` §5). The live
web changes minute to minute; benchmarking against it would make results impossible to
reproduce and trivial to dispute. Yet the live fallback
([ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)) is a genuine real-world
capability worth showing.

## Decision

- **Benchmarks run on the fixed corpus.** Every headline number in the paper is produced
  against the **frozen, versioned medical corpus**, so any reader can re-run the suite
  and obtain the same result — subject to the documented non-determinism handling
  (`EVALUATION.md` §5).
- **The live fallback is a demonstrated capability, not a benchmarked component.** It is
  shown working in the demo and described qualitatively, but it **never contributes to
  the headline metrics.**
- This split is recorded in `EVALUATION.md` so the methodology is unambiguous.

## Consequences

- The corpus is **versioned and frozen** for benchmark runs; corpus changes are
  deliberate and noted, so a result is always tied to a known corpus state.
- `EVALUATION.md` states explicitly which results are corpus-based (all headline numbers)
  and that the live fallback is illustrative only.
- The evaluation stays **honest and reproducible** — the centerpiece remains defensible
  under scrutiny.

## Related

- [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) (corpus vs. fallback),
  `EVALUATION.md` §5 (reproducibility).
