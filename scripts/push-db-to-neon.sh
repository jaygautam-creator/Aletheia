#!/usr/bin/env bash
#
# Push the already-built local Aletheia corpus (Docker Postgres) straight to a
# Neon database.
#
# Why this exists: docs/deployment.md §1 seeds Neon by *re-ingesting* the corpus,
# which re-embeds ~15.4k chunks locally (ONNX) and takes a while. The corpus is
# already built locally (~185 MB), so this streams that database — schema + data —
# directly into Neon instead. It is read-only on the local database; it only writes
# to the Neon target you pass in.
#
# Usage:
#   scripts/push-db-to-neon.sh 'postgresql://USER:PASS@HOST/DB?sslmode=require'
#   # or: NEON_DATABASE_URL='postgresql://…' scripts/push-db-to-neon.sh
#
# Pass the RAW Neon string (the psql form Neon shows). NOT the app's
# 'postgresql+psycopg://…' form — psql/pg_dump do not understand the +psycopg
# driver suffix. The backend (HF Space) uses the +psycopg form; this script does not.
#
# Prereqs: the local stack is up (`make demo-up`), so the Docker Postgres container
# is running — this script borrows that container's pg16 client tools and its
# outbound network to reach Neon, so nothing needs to be installed on the host.

set -euo pipefail

NEON_URL="${1:-${NEON_DATABASE_URL:-}}"

if [ -z "$NEON_URL" ]; then
  echo "usage: $0 'postgresql://USER:PASS@HOST/DB?sslmode=require'" >&2
  echo "  (the RAW Neon connection string — NOT the app's postgresql+psycopg:// form)" >&2
  exit 2
fi

case "$NEON_URL" in
  *"+psycopg"*)
    echo "error: strip the '+psycopg' from the URL — pg_dump/psql need the raw" >&2
    echo "       'postgresql://…' form. (The '+psycopg' form is only for the app.)" >&2
    exit 2
    ;;
  postgresql://*|postgres://*) : ;;
  *)
    echo "error: expected a 'postgresql://…' URL, got: ${NEON_URL%%:*}:…" >&2
    exit 2
    ;;
esac

# A second '?' means two query strings were concatenated (e.g. the Neon string was
# pasted into a template that already had '?sslmode=require'). libpq then misparses the
# params ("extra key/value separator"). Refuse rather than fail cryptically in psql.
case "$NEON_URL" in
  *\?*\?*)
    echo "error: the URL has two '?' — you likely pasted the Neon string into a" >&2
    echo "       template that already had '?sslmode=require'. Pass the raw Neon" >&2
    echo "       string ALONE, exactly as Neon shows it, in single quotes." >&2
    exit 2
    ;;
esac

# Neon's pooled endpoint (…-pooler.…) is PgBouncer; pg_dump needs a session-level
# snapshot the pooler can't provide, so rewrite to the direct endpoint automatically.
case "$NEON_URL" in
  *-pooler.*)
    NEON_URL="${NEON_URL/-pooler./.}"
    echo "note: using Neon's DIRECT endpoint for the dump (the pooler can't do pg_dump)." >&2
    ;;
esac

# Reject the obvious foot-gun: pushing to the local DB itself.
case "$NEON_URL" in
  *localhost*|*127.0.0.1*|*@postgres[:/]*)
    echo "error: that looks like the LOCAL database, not Neon. Refusing." >&2
    exit 2
    ;;
esac

compose() { docker compose "$@"; }

if ! compose exec -T postgres pg_isready -U aletheia -d aletheia >/dev/null 2>&1; then
  echo "error: local Docker Postgres is not up. Run 'make demo-up' first." >&2
  exit 1
fi

echo "==> Local corpus (source of truth):"
compose exec -T postgres psql -U aletheia -d aletheia -tc \
  "SELECT 'chunk=' || count(*) FROM chunk;" | tr -d ' '

echo "==> Streaming schema + data  local ──▶ Neon  (this can take a minute)…"
# One pipe, entirely inside the container: pg_dump reads local, psql writes Neon.
#   --no-owner / --no-privileges : the Neon role differs from the local 'aletheia' role.
#   --no-comments : avoids 'COMMENT ON EXTENSION vector' failing on managed Postgres.
# NEON_URL is passed as an env var (never interpolated into the shell string) so a
# password with shell metacharacters can't break or leak.
# shellcheck disable=SC2016  # $NEON_URL must expand in the container shell, not here.
compose exec -T -e NEON_URL="$NEON_URL" postgres sh -c '
  set -e
  psql "$NEON_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
  pg_dump -U aletheia -d aletheia --no-owner --no-privileges --no-comments \
    | psql "$NEON_URL"
'

echo "==> Verifying row counts on Neon (real counts, not stale stats):"
# shellcheck disable=SC2016  # $NEON_URL must expand in the container shell, not here.
compose exec -T -e NEON_URL="$NEON_URL" postgres sh -c \
  'psql "$NEON_URL" -c "SELECT (SELECT count(*) FROM source) AS source, (SELECT count(*) FROM document) AS document, (SELECT count(*) FROM chunk) AS chunk;"'

echo
echo "Done. If chunk on Neon matches the local count above, the corpus is live."
echo "The backend (HF Space) DATABASE_URL should use the +psycopg form:"
echo "  postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require"
