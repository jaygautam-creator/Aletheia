# ADR 0013 — Multi-source corroboration for the live Wikipedia fallback

- **Status:** Accepted
- **Date:** 2026-07-20 (proposed), 2026-07-24 (accepted)
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

## Decision

Fetch evidence from **two independent free, ToS-compliant sources** instead of one, and
only report the query as having *corroborated* evidence when both agree. The second source
is **tiered, accountable-first** (decided 2026-07-24):

1. **Wikidata's structured API — tried first.** Same foundation as Wikipedia but a genuinely
   different service (structured triples, not prose), so it can independently confirm a
   discrete fact (a date, a nationality, a founding year) even though it shares an umbrella
   organization. It is the more accountable source, so it is asked first.
2. **An allowlisted web source (DuckDuckGo Instant Answer / a fixed accountable-domain list)
   — only when Wikidata returns nothing.** Broader coverage for prose-style general claims
   Wikidata cannot answer, at the cost of accountability, so it is a fallback, never the
   primary corroborator. It is constrained to an explicit domain allowlist (Wikipedia,
   Wikidata, `.gov`, established reference works) so "trustable" always means *accountable
   source class + verbatim span + independent agreement*, never an arbitrary URL.

This "both, tiered" ordering keeps the most accountable source in the primary slot while
still covering claims structured data misses — the coverage of the broader source without
letting it become the sole basis for an upgrade.

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

## Resolved decisions

- **Second source (2026-07-24): both, tiered.** Wikidata first (accountable, structured);
  an allowlisted web source only when Wikidata has nothing. Rationale above.
- **Trust-label shape (2026-07-24): a `corroborated: bool` flag on the existing
  `LIVE_FALLBACK` tier, not a new enum value.** Smaller schema change, avoids touching every
  `TrustTier` match site, and expresses exactly what we mean — the same low-trust live tier,
  now with an independent second source agreeing. A new enum can come later if the flag
  proves insufficient.

## Open questions

- The exact allowlist for the web-fallback source is deferred to implementation — start
  narrow (Wikipedia, Wikidata, `.gov`) and widen only with justification.

## Related

[ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) (the tier system this extends),
[ADR-0012](0012-live-wikipedia-fallback-for-general-claims.md) (the path this corroborates),
[ADR-0006](0006-benchmark-on-fixed-corpus.md) (why this is out of scope for benchmark stats).
