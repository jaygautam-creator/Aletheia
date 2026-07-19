# ADR 0012 — Live Wikipedia fallback for general (non-medical) claims

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decided:** completing [ADR-0003](0003-corpus-first-hybrid-knowledge-source.md)'s
  deferred "lower-trust live fallback" step (author-requested, this session)
- **Deciders:** Jay Gautam

## Context

Two ways to verify a claim already ship: search the curated medical corpus (default), or
supply your own evidence in any domain ([ADR-0010](0010-own-document-verification-any-domain.md)).
Neither covers a **general, non-medical claim with no document supplied** — today the
Intake guard's scope classifier refuses it outright ("Aletheia only verifies medical and
health-related claims"). ADR-0003 anticipated exactly this gap and locked its shape two
phases ago: *"When the corpus lacks sufficient evidence for a claim, the system may fall
back to live literature/web search — surfaced as a clearly-marked, lower-trust evidence
tier, never silently mixed in as if it were corpus-grade."* That ADR intentionally
deferred the fallback until the corpus path was solid (Phase 2/3 done) — it is now.

Two things this is **not**: it is not the FEVER corpus slice built for the E4 benchmark
(ADR-0011) — that slice is ~5K pages hand-selected to cover 100 sampled benchmark claims,
useless for an arbitrary live question. And it is not a general web search — scraping
search-engine results has no single accountable source, inconsistent quality, and likely
violates the scraped site's terms of service.

## Decision

**Route every non-medical query to a live, on-demand Wikipedia lookup instead of
refusing it**, via Wikipedia's own REST API (`en.wikipedia.org/w/api.php`) — free,
official, ToS-compliant, one accountable source. This is a live fetch per query, not a
bulk ingest: no corpus to build, freeze, or benchmark.

- **Routing rule:** the Intake guard's scope classifier still runs, but `out_of_scope`
  no longer refuses — it now means "route to the live Wikipedia fallback" instead of
  "route to the medical corpus." Only a prompt-injection match still produces an actual
  refusal. Caller-supplied evidence (ADR-0010) is unaffected and still skips the
  classifier entirely.
- **Trust tier:** results carry `TrustTier.LIVE_FALLBACK` — the tier the schema modelled
  in the very first migration for exactly this day — never `CURATED_CORPUS`. The tier is
  already surfaced end-to-end on every citation (trust tier travels through retrieval,
  the verdict, and the API response), so this is legible per ADR-0003's "never silently
  mixed in" requirement with no new plumbing.
- **Mechanism:** a live-only retriever (`corpus/live/wikipedia.py`) — Wikipedia's search
  API to find the best-matching page, then its extract API for the plain-text summary —
  is a second `EvidenceRetriever` the Retriever node chooses between based on the
  Intake guard's ruling for that request, never both at once.
- **Never benchmarked:** matching ADR-0003's original framing, this is a *demonstrated*
  capability, not a benchmarked component. `EVALUATION.md`'s headline numbers are
  untouched; this never runs inside the harness.

## Consequences

- `TrustTier.LIVE_FALLBACK` moves from modelled-but-unused to actually populated.
- The Intake guard's refusal path now fires only for `injection`, never `out_of_scope`;
  its docstring and the `refusal_node` comment are updated accordingly.
- `VerificationPipeline` gains an optional second retriever (the live fallback),
  selected per-request from the Intake guard's category — additive, the single-retriever
  construction (evaluation harness, own-document mode) is unchanged.
- A general question now gets a real, grounded-or-unverifiable answer instead of a
  decline — closing the gap between "we can measure grounding generalizes" (FEVER) and
  "a user can ask Aletheia a general claim right now."
- Free-tier: Wikipedia's API has no auth and generous rate limits for this call volume;
  no new cost.

## Related

[ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) (the tier and fallback this
completes), [ADR-0010](0010-own-document-verification-any-domain.md) (the other
any-domain path, unaffected), [ADR-0011](0011-fever-second-benchmark-domain.md) (why its
corpus slice can't serve this purpose).
