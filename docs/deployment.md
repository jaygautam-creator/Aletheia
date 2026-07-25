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
3. Seed Neon with the corpus **once**. Two ways:

   **Fast (recommended) — copy the already-built local corpus.** If you have run the
   corpus locally (`make demo-up`), the ~185 MB database already exists; stream it
   straight to Neon instead of re-embedding. Pass the **raw** Neon string (not the
   `+psycopg` form):

   ```sh
   scripts/push-db-to-neon.sh 'postgresql://<neon-connection-string>?sslmode=require'
   ```

   It borrows the Docker Postgres container's client tools (nothing to install), is
   read-only on the local DB, and prints Neon row counts to confirm.

   **From scratch — re-ingest.** If you have no local corpus, apply the schema and
   ingest (this re-embeds ~15.4k chunks locally via ONNX, so it takes a while):

   ```sh
   DATABASE_URL="postgresql+psycopg://<neon-connection-string>" make db-upgrade
   DATABASE_URL="postgresql+psycopg://<neon-connection-string>" \
     uv --directory backend run python -m aletheia.corpus.cli ingest \
     --connector scifact --corpus-file data/scifact/corpus.jsonl
   ```

   Either way, Neon autosuspends when idle and resumes in ~1 s — no action needed.

## 2. Render — the backend

> **Why Render, not Hugging Face.** HF made Docker Spaces on free `cpu-basic` a PRO
> feature (HTTP 402), so the free backend now runs on Render. The HF path is kept below
> for anyone with PRO. The `deploy/huggingface/` config still applies there unchanged.

1. **Render → New → Blueprint**, connect this repo. Render reads `render.yaml` at the
   root and provisions one free Docker web service (`aletheia-backend`) that builds
   `backend/Dockerfile`, serves on the `PORT` Render injects, and health-checks `/health`.
2. In the service's **Environment** tab, set the three secrets `render.yaml` marks
   `sync: false`:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | the Neon `postgresql+psycopg://…` **pooler** string (runtime wants pooling) |
   | `GROQ_API_KEY` | your free Groq key (server-side only) |
   | `CORS_ORIGINS` | the Vercel origin (start with `*` to test, tighten in step 4) |

   The non-secret vars (`APP_ENV=production`, `LLM_PROVIDER=groq`,
   `RATE_LIMIT_PER_MINUTE=6`, `TRUST_PROXY_HEADERS=true`) are already pinned in the
   blueprint.
3. **Keep it warm.** A free service spins down after 15 min idle (~50 s cold start on
   the next hit). Add a free HTTP monitor — [UptimeRobot](https://uptimerobot.com) or
   [cron-job.org](https://cron-job.org) — that GETs `https://<service>.onrender.com/health`
   every 5 min. That keeps it always-on *and* gives uptime monitoring. One always-on free
   service fits Render's 750 instance-hours/month; a second always-on free service would
   not, so keep only this one warmed.
4. If the service OOMs on boot (the 512 MB free RAM is close to the model's footprint),
   flip `plan: free` → `plan: starter` in `render.yaml` ($7/mo) and redeploy.

<details>
<summary>Alternative: Hugging Face Space (requires PRO)</summary>

## 2b. Hugging Face Space — the backend (PRO only)

1. Create a **Docker** Space (free CPU basic: 2 vCPU, 16 GB RAM). Populate it with the
   backend so its Dockerfile builds the image — from a clone of the (empty) Space repo:

   ```sh
   # the Space repo builds its root Dockerfile, so give it the backend as its root
   cp -R backend/. <space-clone>/
   cp deploy/huggingface/README.md <space-clone>/README.md   # carries the Space config
   cd <space-clone> && git add -A && git commit -m "deploy backend" && git push
   ```

   `deploy/huggingface/README.md` already sets `sdk: docker` and `app_port: 8000`
   (the image serves on `${PORT:-8000}`), so no metadata to hand-edit. Do **not** copy
   `.env`/secrets — those are set in the Space UI (next step).
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

</details>

## 3. Vercel — the frontend

1. Import the repo on [vercel.com](https://vercel.com) with the project root set to
   `frontend/`.
2. Set `NEXT_PUBLIC_API_URL` to the backend URL (the Render
   `https://<service>.onrender.com`, or the Space URL e.g.
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
