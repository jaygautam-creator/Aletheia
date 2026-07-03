# ADR 0007 — Free-tier live demo: Vercel + Neon + Hugging Face Spaces

- **Status:** Accepted
- **Date:** 2026-07-03
- **Decided:** at the start of Phase 5 (Production engineering)
- **Deciders:** Jay Gautam

## Context

The charter promises a demo "reachable by a recruiter" without breaking the free-tier
non-negotiable. The system is three deployable parts: a Next.js frontend, a FastAPI
backend that must hold a ~130 MB ONNX embedding model (`BAAI/bge-small-en-v1.5`) in
memory, and a Postgres database with pgvector holding the frozen SciFact corpus
(15.4k chunks × 384-dim vectors plus text — a few tens of MB). The backend also spends
the project's Groq free-tier token budget on every `/verify` call, so a public endpoint
needs abuse protection before it exists ([master plan](../plans/0001-master-improvement-plan.md) D1).

The candidate layouts:

1. **Vercel + Neon + Hugging Face Spaces (Docker).** Vercel's hobby tier serves the
   static/SSR frontend. Neon's free Postgres ships pgvector, comfortably holds the
   corpus, and autosuspends with ~1 s resumes. HF Spaces' free CPU tier (2 vCPU,
   16 GB RAM) runs the backend container; a free Space pauses only after ~48 h without
   traffic, so most visits land warm and a cold wake takes tens of seconds.
2. **Vercel + Neon + Render free web service.** Same shape, but Render's free instance
   has **512 MB RAM** — marginal under the embedder plus FastAPI — and spins down after
   **15 minutes** idle, so nearly every recruiter visit would eat a ~1-minute cold start.
3. **Recorded demo + one-command local run.** Zero ops and zero abuse surface, but a
   recruiter cannot try a claim themselves; the observable live pipeline is one of the
   charter's success criteria.

## Decision

**Deploy layout 1: Vercel (frontend) + Neon (pgvector Postgres) + Hugging Face Spaces
Docker (backend).** Render is rejected on RAM headroom and cold-start frequency, not on
principle. The recorded demo (option 3) remains the documented fallback: if live-demo
ops prove unreasonable in practice (quota exhaustion, platform changes, unacceptable
wake times), the Space is taken down and the README points at a recording plus
`docker compose up` — an honest retreat, not a half-deployed service.

Preconditions for the public endpoint, enforced in code, in this order:

- **Scope guard stays ON** (`scope_guard_enabled` defaults to `true`): out-of-domain
  and prompt-injection queries are refused before they reach the Generator.
- **Per-IP rate limiting**: an in-process token-bucket middleware guards the
  `/verify*` routes (the only LLM-spending endpoints). `RATE_LIMIT_PER_MINUTE=0`
  disables it for local development, **but the app refuses to start with
  `APP_ENV=production` unless the limit is positive** — a public deploy cannot forget
  the limiter. 429 responses carry a `Retry-After` header and a JSON body
  (`detail`, `retry_after_seconds`) shared with the request-hardening work (D5).
- **Proxy-aware client identity, opt-in**: behind the platform proxy the middleware
  reads the last `X-Forwarded-For` entry (the one appended by the trusted proxy) only
  when `TRUST_PROXY_HEADERS=true`; it defaults to the socket peer address so the
  header cannot be spoofed in direct-exposure setups.
- **Keys stay server-side**: the Groq key lives in the Space's secrets; the frontend
  talks to the backend over CORS (`CORS_ORIGINS` set to the Vercel origin,
  `NEXT_PUBLIC_API_URL` set at Vercel build time). The corpus is ingested into Neon
  once, from the local machine.
- **Cold starts are named, not hidden**: the verify page's connection-failure state
  tells deployed-demo visitors the free-tier backend may take up to a minute to wake.

## Consequences

- A recruiter can open the Vercel URL and verify a claim against the real corpus; the
  worst case is a labelled ~1-minute wake, not a mystery hang.
- Abuse of the public endpoint is bounded per IP and the whole endpoint is bounded by
  Groq's own free-tier caps; the failure mode is a clear 429/503, not a surprise bill —
  there is no card on file anywhere in the stack.
- The in-process limiter's counters are per-instance and reset on restart. With one
  free Space instance that is exact; it is deliberately **not** distributed
  state — introducing Redis for this would contradict the D3 honesty rule.
- Deployment steps live in [docs/deployment.md](../deployment.md); local development
  is unchanged (`make dev`, limiter dormant by default).

## Related

- [ADR-0002](0002-verification-not-medical-advice.md) (the disclaimer travels with
  every response, including the public demo), [ADR-0006](0006-benchmark-on-fixed-corpus.md)
  (the demo demonstrates; benchmarks stay corpus-pinned), master plan D1/D5.
