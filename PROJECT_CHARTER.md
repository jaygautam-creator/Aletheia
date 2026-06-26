# Project Charter — Aletheia

> **Status:** Living document. This is the authoritative description of what
> Aletheia is and is not. It is derived from the master brief and takes
> precedence over any single conversation or commit.

## 1. One-line definition

Aletheia is a multi-agent verification framework, with a rigorous evaluation
harness, that improves the reliability of LLM-generated answers by grounding
every claim in real evidence and surfacing disagreement instead of hiding it.

## 2. The problem

Large Language Models confidently produce **hallucinations** — fluent answers
that are factually wrong, or that cite sources which do not actually support the
claim. Critically, a model expresses the *same* high confidence whether it is
right or completely wrong, so users have no reliable signal for which answers to
trust. In high-stakes domains (medical, legal, finance, education), acting on an
unverified wrong answer causes real harm.

Two existing approaches fall short:

- **Single-model self-checking** cannot reliably catch its own mistakes — the
  same weights that produced the error also judge it.
- **Naive multi-agent debate** suffers from **false agreement**: agents reinforce
  each other's errors instead of detecting them, because verdicts are opinions,
  not evidence.

## 3. The solution

A pipeline of specialized agents that collaborate to produce *and verify* an
answer:

1. **Generator** — produces a candidate answer.
2. **Retriever** — fetches candidate evidence from a source corpus using hybrid
   (semantic + keyword) search.
3. **Verifier / Critic** — independently judges each extracted claim as
   `Supported` / `Contradicted` / `Unverifiable`, and **must quote the exact
   source span** that justifies the verdict. This evidence grounding is what
   prevents false agreement: verdicts are tied to text, not opinion.
4. **Aggregator** — produces the final answer, a calibrated confidence score,
   and an explicit list of disagreements/contradictions.
5. **Guardrail layer** — screens inputs for prompt injection and filters unsafe
   content.

The system is **observable**: a user can watch the agents work and follow the
reasoning/verification path live.

## 4. The differentiator (why this is top-tier and paper-worthy)

The **evaluation harness is the centerpiece**, not an afterthought. It runs the
system repeatedly (handling non-determinism) over public benchmark datasets and
measures, against a single-LLM baseline:

- verification accuracy
- hallucination-catch rate
- false-agreement rate
- latency (p50 / p95 / p99)
- per-query cost

**The headline result** is a table proving the multi-agent grounded approach
catches measurably more errors than a single model.

**The research contribution:** most prior work does *either* pure hallucination
detection *or* natural-language-only agent debate. Aletheia's contribution is
**evidence-grounded verification** (every verdict cites source text) inside a
**deployed, evaluated, multi-agent system** with a **reusable evaluation
harness**. The precise novelty claim is validated against current literature in
Phase 3 and refined in `EVALUATION.md`.

## 5. Success criteria

Aletheia is successful when:

1. The evaluation harness produces a reproducible results table showing the
   multi-agent grounded system beats a single-LLM baseline on hallucination-catch
   rate and verification accuracy, with reported latency and cost trade-offs.
2. Every Verifier verdict is backed by a quoted source span (no ungrounded
   verdicts in the final output).
3. The live frontend renders the agent/verification path, confidence, and
   disagreements clearly enough for a non-expert to follow.
4. The whole system runs free-tier and self-hosted via `docker compose up`, with
   green CI and recruiter-grade documentation.
5. A clean preprint-style paper is generated from `EVALUATION.md`.

## 6. Scope boundaries

**In scope:** the agent pipeline, evidence-grounded verification, hybrid
retrieval over a defined corpus, the evaluation harness, a live observability
frontend, and production engineering (containers, CI/CD, metrics) — all on free
tiers.

**Out of scope:** see `ANTI_DRIFT.md` for the explicit do-not-do list. In short:
this is not a general chatbot, not a paid product, and not a sprawling
multi-domain platform.

## 7. Technology stack

| Layer | Choice | Why (free-tier) |
| --- | --- | --- |
| Frontend | Next.js (App Router, TypeScript) | Streaming UI for the live agent path; free on Vercel |
| Backend | FastAPI (async Python) | High-performance async API; runs locally or on free PaaS |
| Orchestration | LangGraph (+ LangChain where helpful) | Supervisor/worker multi-agent state machines |
| Vector store | PostgreSQL + pgvector | Hybrid search; free locally and via free cloud tiers |
| LLM runtime | Gemini / Groq free tiers via env vars | Provider-agnostic; users supply their own keys |
| Cache / queue | Redis | Free locally; used only where it genuinely helps |
| Observability | Prometheus + Grafana, OTel-style tracing | Free, open source |
| Packaging | Docker, docker-compose, Kubernetes manifests | Reproducible; production-grade deployment story |
| CI/CD | GitHub Actions | Free for public repositories |
| Python tooling | uv, ruff, mypy, pytest | Fast, reproducible, free |

Individual choices may be refined when a genuinely better, still-free option
exists; such changes are justified in writing in `ARCHITECTURE.md` and the
progress log.

## 8. Authorship

Sole author: **Jay Gautam**. This is a public, researchable repository presented
as the author's own work. No third-party or automated co-authorship attribution
appears anywhere in this repository.
