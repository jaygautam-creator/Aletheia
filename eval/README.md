# Evaluation harness

> **This is the centerpiece of Aletheia.** Features exist to be measured here.

The harness runs the verification system repeatedly over a public benchmark,
handles non-determinism with seeded runs, logs full agent traces, and computes a
metric suite **against a single-LLM baseline** (and an ungrounded multi-agent
ablation arm):

- verification accuracy
- hallucination-catch rate
- false-agreement rate
- latency (p50 / p95 / p99)
- per-query cost (token accounting)

## Where the code lives

The harness is **inside the backend package**, not in this directory — it imports
the pipeline directly, is tested by the same CI, and shares one lockfile:

```
backend/src/aletheia/evaluation/
├── benchmark.py   # SciFact adapter → BenchmarkItem (gold in the pipeline's verdict space)
├── metrics.py     # scoring, latency/cost, McNemar + bootstrap significance
├── phase1.py      # Phase 1 mini-set comparison (make phase1-demo)
├── phase3.py      # the benchmark runner: grounded vs baseline vs ungrounded ablation
├── report.py      # seeded aggregation → EVALUATION.md §6.2 + the frontend results JSON
└── trace.py       # per-run trace logging (JSONL)
```

This `eval/` directory holds only run notes and generated artifacts (large or
regenerable artifacts are git-ignored).

## Running it

```bash
# Phase 1 mini-set (needs a provider key in .env):
make phase1-demo

# Phase 3 benchmark (needs Postgres + the ingested SciFact corpus + a provider key);
# writes EVALUATION.md §6.2 and the frontend's benchmark-results.json:
make phase3-bench CLAIMS=data/scifact/claims_dev.jsonl

# a fuller live run, seeded, with the ablation arm and repeats:
uv --directory backend run python -m aletheia.evaluation.phase3 \
    --claims data/scifact/claims_dev.jsonl --sample 100 --seed 7 --repeats 3 --ablation \
    --traces runs/scifact.jsonl --write-eval ../EVALUATION.md \
    --write-frontend ../frontend/lib/benchmark-results.json
```

Methodology and results live in [`../EVALUATION.md`](../EVALUATION.md), which
doubles as the spine of the research paper.
