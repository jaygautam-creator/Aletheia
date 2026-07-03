# Deploying the free-tier live demo

This is the step-by-step companion to
[ADR-0007](design/0007-free-tier-live-demo-deployment.md): **Vercel** serves the
frontend, **Neon** holds the pgvector corpus, and a **Hugging Face Space** (Docker)
runs the FastAPI backend. Everything below is on permanent free tiers — no card on
file anywhere. Local development is unaffected (`make dev`).

## 1. Neon — the corpus database

1. Create a free project at [neon.tech](https://neon.tech) (Postgres 16+). pgvector is
   available out of the box; the SciFact corpus (≈15.4k chunks × 384-dim vectors) uses
   a few tens of MB of the 512 MB free storage.
2. Copy the connection string and convert it to the async driver form the app expects:
   `postgresql+psycopg://…` (Neon shows `postgresql://…`; just add `+psycopg`).
3. From the local machine, apply the schema and ingest the corpus **once**:

   ```sh
   DATABASE_URL="postgresql+psycopg://<neon-connection-string>" make db-upgrade
   DATABASE_URL="postgresql+psycopg://<neon-connection-string>" \
     uv --directory backend run python -m aletheia.corpus.cli ingest \
     --connector scifact --corpus-file data/scifact/corpus.jsonl
   ```

   Ingestion embeds locally (ONNX) and writes to Neon; expect it to take a while on
   first run. Neon autosuspends when idle and resumes in ~1 s — no action needed.

## 2. Hugging Face Space — the backend

1. Create a **Docker** Space (free CPU basic: 2 vCPU, 16 GB RAM) and push the
   `backend/` Dockerfile context to it (or configure the Space to track this repo's
   `backend/` directory). Set `app_port: 8000` in the Space's README metadata — the
   image serves on `${PORT:-8000}`.
2. Set the Space **secrets/variables**:

   | Variable | Value |
   | --- | --- |
   | `APP_ENV` | `production` (refuses to boot if the rate limit is off) |
   | `DATABASE_URL` | the Neon `postgresql+psycopg://…` string |
   | `LLM_PROVIDER` / `GROQ_API_KEY` | `groq` + your free key (server-side only) |
   | `RATE_LIMIT_PER_MINUTE` | e.g. `6` (with the default burst of 10) |
   | `TRUST_PROXY_HEADERS` | `true` (the Space sits behind HF's proxy) |
   | `CORS_ORIGINS` | the Vercel origin, e.g. `https://aletheia.vercel.app` |
   | `SCOPE_GUARD_ENABLED` | leave defaulted (`true`) |

3. A free Space pauses after ~48 h without traffic; the first visit after that eats a
   cold start (tens of seconds). The frontend names this instead of hiding it.

## 3. Vercel — the frontend

1. Import the repo on [vercel.com](https://vercel.com) with the project root set to
   `frontend/`.
2. Set `NEXT_PUBLIC_API_URL` to the Space URL (e.g.
   `https://<user>-aletheia.hf.space`) for Production. This is inlined at build time —
   redeploy after changing it. It also switches the verify page's connection-failure
   hint from the local `make dev` tip to the free-tier wake-up explanation.

## 4. Verify the deployment

```sh
curl https://<space-url>/health          # {"status":"ok",...}
curl -X POST https://<space-url>/verify -H 'content-type: application/json' \
  -d '{"query":"Does aspirin reduce the risk of heart attack?"}'
```

Then open the Vercel URL and run a claim end-to-end. Confirm a burst of repeated
requests returns `429` with a `Retry-After` header — the limiter must be live before
the URL is shared anywhere.

## Fallback (decided in ADR-0007)

If the live demo's ops cost turns unreasonable — quota exhaustion, platform changes,
unacceptable wake times — take the Space down, point the README at a recorded demo,
and keep the one-command local run (`docker compose up`) as the reproducible path.
