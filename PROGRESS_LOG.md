# Progress Log

A running, plain-language record of what was accomplished each session — written
so a non-expert (e.g., an academic mentor) can understand the progress at a
glance. Newest entries first.

---

## 2026-06-29 — Phase 3: The evaluation harness

**What got done, in plain language:**

- Built the project's **centerpiece**: a repeatable test bench that pits the grounded
  multi-agent system against an ordinary single AI model on the *same* questions and
  *measures the difference* — the whole point of the project.
- Adopted a real, published medical benchmark — **SciFact** (expert-written scientific
  claims, each labelled against biomedical abstracts) — and grew the system's searchable
  library to include SciFact's abstracts, so the system genuinely looks up evidence for
  each claim instead of being handed it.
- Defined the **scorecard**: how often each system correctly catches an unsupported claim,
  how often it wrongly "agrees" a claim is true when it isn't, how fast it answers
  (typical and worst-case), and how many tokens it costs — every number reported next to
  the single-model baseline so it's always a comparison.
- Made every run **fully auditable**: each question's inputs, the evidence pulled up, the
  verdicts, and the timing/token cost are written to a log file, so any result can be
  traced and inspected.
- Wired it into **one command** that runs the comparison several times (to handle the
  randomness of AI models), averages the results with error bars, and writes the headline
  table straight into the evaluation document.
- Positioned the work against existing research honestly: it's the *combination* —
  evidence-quoting agreement inside a deployed, measured system — that's the contribution,
  and the claim is scoped to the measured gap rather than a grand "first ever".

**Why this matters:** Phases 1–2 proved the idea works and made it retrieve its own
evidence. Phase 3 makes the project *scientific*: it can now produce defensible,
reproducible numbers showing whether — and by how much — grounded multi-agent verification
beats a single model. The machinery is complete and tested without any API key; the
headline numbers themselves are produced by running it live against the corpus, and the
novelty positioning will be finalised against a full literature search at paper time.

**Next up (Phase 4):** A real-time frontend that streams the live verification path —
the reasoning, the confidence, and the explicit disagreements — into a clean, legible UI.

---

## 2026-06-29 — Phase 2: Retrieval & grounding

**What got done, in plain language:**

- Gave the system a **memory it can search**: a PostgreSQL database with a
  vector-search extension, where curated medical literature is stored as small,
  individually searchable passages (built in Phase 0/early Phase 2).
- Built the **ingestion pipeline** that turns a real source (a PubMed/PMC
  article) into those passages — fetching it, cleaning it, splitting it into
  chunks, and computing a numerical "fingerprint" (an *embedding*) for each so it
  can be found by meaning, not just by exact words. The embeddings are produced by
  a **local, free model** by default, so the corpus is reproducible with no API
  bills and no network.
- Added **hybrid retrieval**: every search runs two ways at once — by *meaning*
  (vector similarity) and by *keyword* (classic full-text match) — and the two
  result lists are blended with a standard ranking-fusion method so a passage that
  both methods like rises to the top. Each result carries its source's trust level,
  so the verifier never grounds a claim in untiered evidence.
- **Wired retrieval into the pipeline.** Previously you had to hand the system the
  evidence; now, when you don't, it **finds its own evidence** from the corpus,
  grounds the verdicts in it, and returns the exact sources it used as citations.
  Importantly, the existing verdict format was left untouched — citations and the
  safety notice are *added alongside*, so nothing that already worked broke.
- Added an **output guardrail**: a final, read-only step that reads the finished
  result and attaches a plain advisory — *info* when every claim is supported,
  *caution* when something couldn't be verified, *high caution* when the evidence
  contradicts a claim — together with a standing notice that the system does not
  give medical advice. It never edits a verdict; it only labels the result.
- Made the database-backed tests **run automatically in CI**: every change now
  spins up a throwaway PostgreSQL + vector database in the cloud and runs the
  ingestion and retrieval tests against a real database, not a mock.

**Why this matters:** Phase 1 proved the idea on hand-fed evidence. Phase 2
removes the training wheels — the system now retrieves its own evidence from a
real, searchable corpus and still refuses to affirm anything it can't quote,
while clearly flagging uncertainty and contradictions. That is the difference
between a demo and a tool you could point at a genuine question.

**Next up (Phase 3):** The evaluation harness — repeatable, seeded runs over
public benchmarks that measure, with numbers, how much the grounded multi-agent
approach beats a single model on catching hallucinations.

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
