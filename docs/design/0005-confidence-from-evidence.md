# ADR 0005 — Confidence is explained by evidence, never an unexplained number

- **Status:** Accepted (locked)
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

A bare confidence score is the same trap as a confident LLM: a number with no traceable
basis invites misplaced trust. Aletheia's whole premise is that trust must be *earned by
evidence*. This is why today's contract deliberately calls its provisional signal
`support_ratio` and **not** "confidence" — the name "confidence" is reserved for a value
that is genuinely explained and, in Phase 3, calibrated.

## Decision

Confidence is **derived from, and reported with, the factors that produced it.** It is a
function of:

- **evidence agreement** — how strongly the retrieved evidence concurs versus conflicts
  ([ADR-0004](0004-surface-disagreement.md)), and
- **source trust tier** — corpus-grade versus lower-trust fallback
  ([ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)).

Every confidence value the system emits is **accompanied by the factors that produced
it.** There is no unexplained scalar anywhere — not in the output, the API, or the UI.
Calibrating this score against gold labels is the work of the Phase 3 evaluation
harness; until then the system reports the contributing factors honestly rather than a
falsely precise number.

## Consequences

- The result contract carries a confidence **and its explanation** (the contributing
  factors), never a lone float.
- Confidence cannot be computed without trust tiers and the disagreement weighting, so
  [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) and
  [ADR-0004](0004-surface-disagreement.md) are prerequisites.
- In the medical framing ([ADR-0002](0002-verification-not-medical-advice.md)),
  confidence describes **evidence strength, not clinical certainty**, and is shown beside
  the not-medical-advice disclaimer.

## Related

- [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md),
  [ADR-0004](0004-surface-disagreement.md); `EVALUATION.md` (calibration in Phase 3).
