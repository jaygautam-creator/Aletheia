# ADR 0013 — Multi-source corroboration for the live Wikipedia fallback

- **Status:** Proposed
- **Date:** 2026-07-20
- **Deciders:** Jay Gautam

## Context

[ADR-0012](0012-live-wikipedia-fallback-for-general-claims.md) added a live, single-source
Wikipedia lookup for general (non-medical) claims with no document supplied. It works, but
it is the least-corroborated evidence path in the system: one page, one API call, no
second opinion. Every other tier has an implicit corroboration story already —
`curated_corpus` sources were hand-selected/vetted at ingestion, `own_document` is
whatever the user vouches for themselves. `live_fallback` alone rests entirely on
"Wikipedia's top search hit happened to be right."

**This is not a fix for the FEVER/SciFact benchmark numbers.** Those benchmarks score
against a fixed, single evidence corpus per claim ([ADR-0006](0006-benchmark-on-fixed-corpus.md))
— there is no second independent source to cross-check there, and *requiring* agreement
would only make the grounded Verifier's already-strict quoted-span rule stricter, worsening
the over-abstention problem the 2026-07-20 prompt fix is targeting. This ADR is scoped
purely to raising trust on the live-fallback path; it does not touch the benchmark harness
or `EVALUATION.md`.

## Decision (proposed)

Fetch evidence from **two independent free, ToS-compliant sources** instead of one, and
only report the query as having *corroborated* evidence when both agree. Candidates for
the second source, in order of preference:

1. **Wikidata's structured API** — same foundation as Wikipedia, but a genuinely different
   service (structured triples, not prose), so it can independently confirm a discrete fact
   (a date, a nationality, a founding year) even though it shares an umbrella organization.
2. **DuckDuckGo's Instant Answer API** — free, no auth, pulls from a different aggregation
   of sources than Wikipedia's own search index; weaker guarantees on stability/accountability
   than Wikidata, so second choice.

Mechanism sketch:

- `live_wikipedia.py` gains a sibling lookup for the second source, called in parallel
  with the existing Wikipedia fetch (both are already async).
- A new tier, `TrustTier.LIVE_FALLBACK_CORROBORATED`, sits between `LIVE_FALLBACK` and
  `CURATED_CORPUS` — used only when both sources return evidence and the Verifier's
  existing span-quoting mechanism finds a decisive span in each independently. Disagreement
  (or the second source returning nothing) keeps the citation at plain `LIVE_FALLBACK` —
  it never silently upgrades on partial evidence.
- No change to the Verifier's core quoting logic — corroboration is a retrieval-time
  upgrade to the evidence's trust label, not a new verdict path.

## Consequences

- A genuine trust-tier addition (schema/enum change), so it needs a migration and touches
  every place `TrustTier` is matched on (citations UI, API response, retrieval).
- Adds real latency and cost to the live-fallback path — one more live API call per
  general query, roughly doubling this path's external round-trip time.
- Does **not** move SciFact/FEVER benchmark numbers — those are corpus-only, tracked
  separately (see [[aletheia-fever-live-run-and-verifier-fix]] for what actually does).
- Disagreement between sources is itself informative and could eventually surface as its
  own signal ("sources conflict on this") rather than being silently dropped to the lower
  tier — deferred; out of scope for the first cut.

## Open questions (why this is Proposed, not Accepted)

- Wikidata vs. DuckDuckGo as the second source — Wikidata is structurally cleaner for
  discrete facts but weak on prose-style general claims; DuckDuckGo is broader but a less
  accountable single point of truth. Needs a small live spike before committing.
- Whether `LIVE_FALLBACK_CORROBORATED` is worth a new enum value vs. just a boolean
  `corroborated: bool` flag alongside the existing `LIVE_FALLBACK` tier — the latter is a
  smaller schema change and may be enough.

## Related

[ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) (the tier system this extends),
[ADR-0012](0012-live-wikipedia-fallback-for-general-claims.md) (the path this corroborates),
[ADR-0006](0006-benchmark-on-fixed-corpus.md) (why this is out of scope for benchmark stats).
