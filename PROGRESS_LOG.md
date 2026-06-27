# Progress Log

A running, plain-language record of what was accomplished each session — written
so a non-expert (e.g., an academic mentor) can understand the progress at a
glance. Newest entries first.

---

## 2026-06-27 — Phase 1: Prove the thesis

**What got done, in plain language:**

- Built the first two "thinking" agents and wired them together as an
  inspectable assembly line: a **Generator** that breaks an answer into small,
  individually checkable claims, and a **Verifier** that judges each claim
  *only against supplied evidence*.
- Made the central rule of the whole project unbreakable in code: the Verifier
  may say a claim is supported **only if it can quote the exact words of the
  evidence that back it up**. If it cannot find those words — or invents a
  quote — the system automatically downgrades its answer to "can't verify"
  rather than trusting it. Wrong-but-confident answers have nowhere to hide.
- Made the system **work with any AI provider** behind a single clean switch
  (Google Gemini by default, Groq as a fast alternative), with keys supplied
  privately and never stored in the project.
- Wrote a small **test set with deliberately planted false claims** and a
  one-command comparison that puts our grounded approach next to an ordinary
  single AI model on the *same* claims — measuring how many planted falsehoods
  each one catches.
- Added a web endpoint (`POST /verify`) so the verification can be called like
  a real service, returning each verdict with its supporting quote.
- Everything is covered by automated tests that run without any API key, so the
  quality pipeline stays green for anyone.

**Why this matters:** This is the make-or-break phase. Before investing in
retrieval, a benchmark harness, and a polished interface, it proves the core
idea actually works — that grounding verdicts in quoted evidence catches errors
a single confident model waves through. The headline numbers come from running
the comparison live with a free API key (`make phase1-demo`); the machinery,
the dataset, and the measurement are all in place.

**Next up (Phase 2):** Replace the hand-supplied evidence with real **retrieval**
— a searchable corpus (PostgreSQL + pgvector, hybrid semantic + keyword search)
— plus a guardrail layer, so the Verifier grounds its quotes in evidence the
system finds for itself.

---

## 2026-06-26 — Phase 0: Foundation & Governance

**What got done, in plain language:**

- Created the project's public home on GitHub and set up version control so every
  change is tracked and attributed to me.
- Wrote the project's "constitution": a charter that defines exactly what Aletheia
  is and why it matters, and an anti-drift guide that lists what the project will
  deliberately *not* do, so the work stays focused over the coming months.
- Laid out the full plan as a phase-by-phase roadmap with checkboxes, so progress
  is always visible at a glance.
- Wrote the architecture document (how the pieces fit together) and an evaluation
  plan (how we will *prove*, with numbers, that the system works better than a
  single AI model).
- Built the skeleton of the two main applications: the backend service (the
  "engine") and the frontend website (the "dashboard"), each with a basic working
  page and an automated test confirming it runs.
- Set up the supporting infrastructure: containerization (so anyone can run the
  whole system with one command), a database with vector search, and a cache.
- Added an automated quality pipeline that checks the code on every change, and
  developer shortcuts so common tasks are one command away.

**Why this matters:** This phase builds none of the "smart" features yet — on
purpose. It establishes a professional, reproducible foundation so that every
later phase is fast, safe, and presentable. The next phase proves the core idea.

**Next up (Phase 1):** Build a minimal two-agent pipeline and demonstrate the
verifier catching a deliberately planted false claim that a single AI model
misses — validating the central thesis before building everything else.
