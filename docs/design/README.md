# Design decisions

This directory holds Aletheia's **Architecture Decision Records (ADRs)** — short,
numbered notes that each capture one significant design decision: the context that
forced it, the decision itself, and the consequences it commits the project to.

An ADR records the *why* behind a choice so a reviewer can reconstruct the reasoning
without archaeology through commits. The documents divide the labour cleanly:

- [`PROJECT_CHARTER.md`](../../PROJECT_CHARTER.md) — *what* Aletheia is and is not.
- [`ANTI_DRIFT.md`](../../ANTI_DRIFT.md) — what it must **never** become.
- [`ARCHITECTURE.md`](../../ARCHITECTURE.md) — *how* the pieces fit together.
- **These ADRs** — the pivotal *decisions* those documents depend on.

Decisions are **locked** once accepted. A locked decision is not rewritten in place;
it is changed by adding a new ADR that supersedes it, with both notes pointing at the
other.

## Records

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-domain-focus-medical.md) | Medical domain first, on a domain-agnostic engine | Accepted |
| [0002](0002-verification-not-medical-advice.md) | Aletheia verifies claims; it never gives medical advice | Accepted |
| [0003](0003-corpus-first-hybrid-knowledge-source.md) | Corpus-first knowledge, with a clearly-marked lower-trust live fallback | Accepted |
| [0004](0004-surface-disagreement.md) | Always surface disagreement — never hide it | Accepted |
| [0005](0005-confidence-from-evidence.md) | Confidence is explained by evidence, never an unexplained number | Accepted |
| [0006](0006-benchmark-on-fixed-corpus.md) | Benchmark on the fixed corpus; the live fallback is demonstrated, not benchmarked | Accepted |
| [0007](0007-free-tier-live-demo-deployment.md) | Free-tier live demo on Vercel + Neon + HF Spaces, with the limiter and scope guard as preconditions | Accepted |
| [0008](0008-remove-redis.md) | Remove Redis: no cache has earned its place; the reintroduction shape is documented | Accepted |
| [0009](0009-multimodal-claim-intake.md) | PDF/image/voice claim intake is presentation-layer plumbing; the pipeline and harness are untouched | Accepted |
| [0010](0010-own-document-verification-any-domain.md) | Own-document verification is any-domain: the medical-scope rule guards the corpus, not the engine | Accepted |
| [0011](0011-fever-second-benchmark-domain.md) | FEVER as a second benchmark domain, on a scoped corpus slice sized like SciFact | Accepted |
| [0012](0012-live-wikipedia-fallback-for-general-claims.md) | Live Wikipedia fallback for general (non-medical) claims, completing ADR-0003's deferred lower-trust tier | Accepted |

The first six were decided together, ahead of Phase 2, so that retrieval, grounding,
and evaluation are all built toward the same target; 0007 opens Phase 5.
