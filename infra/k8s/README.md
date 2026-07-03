# Kubernetes reference manifests

**Reference, not a maintained production target.** The deployed demo runs on free
PaaS tiers ([ADR-0007](../../docs/design/0007-free-tier-live-demo-deployment.md));
these manifests exist to show the shape of a cluster deployment of the same
topology as `docker-compose.yml`. They are validated in CI — the kustomization is
rendered and every object checked against the Kubernetes API schemas
(`kubectl kustomize` + `kubeconform`) — but they are not load-tested, carry no
Ingress/TLS story, and anything beyond this would be scope theater for a solo
free-tier project.

## Contents

- `kustomization.yaml` — ties the set together (namespace `aletheia`)
- `namespace.yaml`
- `configmap.yaml` — non-secret settings (production posture: limiter on, JSON logs)
- `secret.example.yaml` — copy to `secret.yaml` (gitignored), fill in, apply separately
- `postgres.yaml` — StatefulSet + headless Service, pgvector image, 2 Gi PVC
- `backend.yaml` — Deployment + Service, health probes, config/secret `envFrom`
- `frontend.yaml` — Deployment + Service

## Usage

```bash
# Validate (what CI does)
kubectl kustomize . | kubeconform -strict -summary -

# Apply, after creating the secret
cp secret.example.yaml secret.yaml   # fill in real values; never commit
kubectl apply -f secret.yaml
kubectl apply -k .
```

Notes: the images are local reference names (`aletheia-backend:local`,
`aletheia-frontend:local`) — build them from the repo's Dockerfiles or point at
your own registry. `NEXT_PUBLIC_API_URL` is inlined into the frontend at **build**
time, so it is a `--build-arg`, not a runtime env var. After first start, run the
Alembic migrations and corpus ingestion against the cluster's Postgres the same
way the [deployment guide](../../docs/deployment.md) does against Neon.
