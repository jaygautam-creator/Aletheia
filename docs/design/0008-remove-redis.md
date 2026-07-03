# ADR 0008 — Remove Redis: no cache has earned its place

- **Status:** Accepted
- **Date:** 2026-07-03
- **Decided:** during Phase 5 (Production engineering)
- **Deciders:** Jay Gautam

## Context

Redis has sat in `docker-compose.yml` since the Phase 0 scaffold, labelled "used only
where it genuinely helps". Five phases later, not one line of backend code references
it — the only matches for "redis" in the source tree are the word "redistributable".
The master plan (D3) demands the decision be made honestly rather than left as
compose-file furniture: keep exactly one genuinely useful cache, or remove Redis
entirely.

The one candidate worth evaluating was a **query → retrieval-results cache** around
`Retriever.search` (embedding + two SQL branches + RRF — the deterministic part of a
request). Weighed against the system as it actually runs:

- Retrieval is **sub-second and local**: the ONNX embedder is in-process and the two
  SQL branches hit an indexed table. The request's cost lives in the 10–20 s of LLM
  calls that follow. A cache would shave under ~10 % of latency at demo-scale
  traffic — approximately nothing.
- The deployment target has nowhere to put it: the free-tier layout
  ([ADR-0007](0007-free-tier-live-demo-deployment.md)) is a single Hugging Face
  Space with no Redis; a managed free tier (e.g. Upstash) would add an account, a
  key, and a failure mode to buy that non-benefit. The rate limiter already chose
  in-process state over shared state for the same reason.
- The benchmark must not cache anyway ([ADR-0006](0006-benchmark-on-fixed-corpus.md)
  and the harness's fairness contract): headline latency measures each system's own
  work. Caching LLM outputs is ruled out separately — it would fake the live
  verification demo.

## Decision

**Remove Redis everywhere it appears**: the compose service, the backend's
`depends_on`, `REDIS_URL` in the environment surface, and the stack tables in the
README, charter, and architecture doc. No cache layer replaces it — there is nothing
worth caching at this scale.

If the math changes (real traffic, multiple instances), the reintroduction shape is
already designed and deliberately small: a `RedisRetrievalCache` wrapping
`Retriever.search` — key = normalised query + corpus manifest hash, TTL ~1 h, guarded
by an optional `REDIS_URL` setting, `fakeredis` tests, and behaviour byte-identical
with the cache disabled. That is a one-file change, and this ADR is where its
justification will live.

## Consequences

- One less container to pull, start, and health-check in every local `docker compose
  up`; one less unused knob in `.env.example`.
- The compose file now states the truth: every service in it is load-bearing.
- LLM outputs are never cached, in any future revision — a cached verdict would
  defeat both the live demo and the evaluation.

## Related

- [ADR-0006](0006-benchmark-on-fixed-corpus.md) (benchmark fairness),
  [ADR-0007](0007-free-tier-live-demo-deployment.md) (single-instance free-tier
  deployment; in-process rate limiting), master plan D3.
