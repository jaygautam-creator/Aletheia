---
title: Aletheia Backend
emoji: 🔎
colorFrom: teal
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
short_description: Evidence-grounded claim verification API (FastAPI).
---

# Aletheia — backend API

This Space runs the FastAPI backend for [Aletheia](https://github.com/jaygautam-creator/Aletheia),
an evidence-grounded, multi-agent claim-verification system. The frontend lives on
Vercel; this Space only serves the API (`/health`, `/verify`, `/verify/stream`).

`app_port: 8000` matches the image, which serves on `${PORT:-8000}` — see
`backend/Dockerfile`. Configuration is supplied entirely through Space **secrets**
(never committed): `DATABASE_URL` (the Neon `postgresql+psycopg://…` string),
`APP_ENV=production`, `GROQ_API_KEY`, `RATE_LIMIT_PER_MINUTE`, `TRUST_PROXY_HEADERS=true`,
and `CORS_ORIGINS` (the Vercel origin). Full runbook: `docs/deployment.md` in the repo.

> This README's front-matter is the Space's configuration. The rest of the Space's
> files are the contents of the repo's `backend/` directory (its `Dockerfile` builds
> the image). See the "populate the Space" step in `docs/deployment.md`.
