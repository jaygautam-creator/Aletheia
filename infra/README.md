# Infrastructure

Deployment and operations assets for Aletheia.

For local development, the full stack runs from the repository root:

```bash
docker compose up --build
```

This directory holds the **production-grade deployment story**, which is built out
in Phase 5:

```
infra/
├── k8s/            # Kubernetes manifests (Deployments, Services, Ingress, config)
└── observability/  # Prometheus + Grafana configuration (added in Phase 5)
```

- **Kubernetes** manifests provide a portable, production-style deployment target.
- **Observability** wires Prometheus metrics and Grafana dashboards for latency,
  cost, and agent metrics, plus OpenTelemetry-style tracing of agent runs.

Everything here targets free, self-hostable, open-source tooling — no paid
dependencies.
