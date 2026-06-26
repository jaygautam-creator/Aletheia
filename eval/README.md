# Evaluation harness

> **This is the centerpiece of Aletheia.** Features exist to be measured here.

The evaluation harness runs the verification system repeatedly over public
hallucination/factuality benchmarks, handles non-determinism, logs full agent
traces, and computes a metric suite **against a single-LLM baseline**:

- verification accuracy
- hallucination-catch rate
- false-agreement rate
- latency (p50 / p95 / p99)
- per-query cost

It is implemented in **Phase 3** and its methodology and results live in
[`../EVALUATION.md`](../EVALUATION.md), which doubles as the spine of the research
paper.

Planned layout:

```
eval/
├── datasets/   # loaders for public benchmarks (HaluEval, FACTS-style sets)
├── runners/    # baseline (single-LLM) and Aletheia run drivers
├── metrics/    # metric implementations
├── results/    # generated result tables and run artifacts
└── report.py   # renders the headline comparison table into EVALUATION.md
```

Datasets are free and citable; large or regenerable artifacts are git-ignored.
