# Kubernetes manifests

Production-style deployment manifests for Aletheia, added in **Phase 5**.

Planned contents:

- `namespace.yaml` — isolated `aletheia` namespace
- `backend.yaml` — Deployment + Service for the FastAPI service
- `frontend.yaml` — Deployment + Service for the Next.js dashboard
- `postgres.yaml` — StatefulSet + Service for PostgreSQL + pgvector
- `redis.yaml` — Deployment + Service for Redis
- `ingress.yaml` — external routing
- `configmap.yaml` / `secret.example.yaml` — configuration (no real secrets committed)

The manifests mirror the local `docker-compose.yml` topology so behaviour is
consistent from laptop to cluster.
