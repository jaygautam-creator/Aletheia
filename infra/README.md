# Infrastructure

Deployment and operations assets. For local development, the full stack runs from
the repository root:

```bash
docker compose up --build
docker compose --profile obs up   # + Prometheus (:9090) and Grafana (:3001)
```

```
infra/
├── k8s/            # Reference Kubernetes manifests — validated in CI, not a
│                   # maintained production target (see k8s/README.md)
└── observability/  # Prometheus scrape config + auto-provisioned Grafana dashboard
                    # for the compose `obs` profile
```

The *deployed* demo does not use Kubernetes: it runs on free PaaS tiers, decided in
[ADR-0007](../docs/design/0007-free-tier-live-demo-deployment.md) and documented
step-by-step in [docs/deployment.md](../docs/deployment.md). Everything here targets
free, self-hostable, open-source tooling — no paid dependencies.
