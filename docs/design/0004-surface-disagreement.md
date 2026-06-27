# ADR 0004 — Always surface disagreement, never hide it

- **Status:** Accepted (locked)
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

Aletheia's thesis is not merely "catch errors" but "surface disagreement instead of
hiding it" (`PROJECT_CHARTER.md` §1). Real literature conflicts — studies contradict one
another, guidance is updated, and sources vary in quality. A system that silently picks
one side and hides the rest reproduces exactly the confidently-wrong behaviour Aletheia
exists to fix.

## Decision

When evidence conflicts, Aletheia **always surfaces the disagreement.** The Aggregator:

1. Presents a clear **primary answer first** — the best-supported position — so the
   output is usable rather than a shrug.
2. **Transparently shows the conflicting evidence** alongside it.
3. **Explains the weighting** — *why* the primary side carries the weight it does versus
   the dissent — in terms of:
   - **recency**,
   - **source trust tier** ([ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)), and
   - **the number of corroborating sources**.

Disagreement is never collapsed into a single verdict, and never dropped to make the
output look more confident.

## Consequences

- The Aggregator's output — and the result contract that feeds the UI in Phase 4 —
  carries not just a primary answer but the **dissenting evidence** and the **factors
  that decided the ranking**.
- This depends on trust tiers ([ADR-0003](0003-corpus-first-hybrid-knowledge-source.md))
  and feeds directly into the explained confidence
  ([ADR-0005](0005-confidence-from-evidence.md)): the same factors that weigh the
  disagreement also explain the confidence.
- `VerificationResult` already separates supported from flagged verdicts; the
  disagreement view is built on that grounded substrate, not on a new opinion layer.

## Related

- [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) (trust tiers),
  [ADR-0005](0005-confidence-from-evidence.md) (explained confidence).
