# Progress Log

A running, plain-language record of what was accomplished each session — written
so a non-expert (e.g., an academic mentor) can understand the progress at a
glance. Newest entries first.

---

## 2026-07-02 — "Refined Luminous": a premium, animated front end + a benchmark page

**What got done, in plain language:**

- **Rebuilt the whole look and feel** into a cohesive premium medical aesthetic — a
  warm light canvas lit by a living aurora that drifts and parallaxes as you scroll,
  layered glass cards that lift and glow on hover, and big editorial serif headlines.
- **Added a signature hero animation:** an interactive "aperture" — concentric rings
  with a sweeping evidence beam that reveals a grounded verdict at its centre, tilting
  toward the cursor. It's the project's name (ἀλήθεια, "unconcealment") made visual.
- **Made the numbers come alive:** the headline stats count up on entry, the benchmark
  bars grow and their labels count up when scrolled into view, and the five-agent
  pipeline is now a live flowing diagram rather than a static list. All motion is
  disabled cleanly for anyone who prefers reduced motion.
- **Built a dedicated `/benchmark` page** — the full results table (all systems, with
  the grounded row highlighted), the animated comparison chart, and a plain-language
  methodology section (three arms, seeded and reproducible, paired significance). This
  turns the evaluation centerpiece into a real page instead of only a markdown file.
- **Kept the numbers honest and single-sourced:** every figure the site shows now comes
  from one generated record the benchmark run writes, so the site can never drift from
  `EVALUATION.md`.

**Why this matters:** the front end now looks like a serious, modern product and *shows*
the work — the animation and polish signal craft, while the specimen, the live chart,
and the benchmark page keep it grounded in real, measured results.

**Next up:** the documentation truth-pass (architecture diagrams) and the remaining
evaluation-runner hardening.

---

## 2026-07-02 — Evaluation rigor (ablation + significance) and a rebuilt front end

**What got done, in plain language:**

- **Added the missing comparison the thesis actually rests on.** The benchmark now
  runs a third system on demand: the *same* multi-agent verifier **with the
  evidence-quoting rule switched off**. Comparing it against the real (grounded)
  system isolates exactly what the "must quote a source span" discipline
  contributes — which is the precise thing Hypothesis H2 claims. Its prompt is a
  word-for-word copy of the real one minus the span rule, so the comparison is fair,
  and that fairness requirement is written down next to the prompt so no future
  change can quietly break it.
- **Made the headline numbers statistically honest.** Because every system judges the
  *same* claims, the harness now reports whether a gap is real rather than noise: an
  exact McNemar test on accuracy and bootstrap confidence intervals on the
  catch-rate and false-agreement gaps, generated straight into the results file. At
  the current small sample this will mostly show the gaps are *not yet* significant —
  which is the honest thing to report, and exactly why scaling the run is next.
- **Rebuilt the landing page and the verification page from the ground up.** The
  landing page now leads with a **real specimen of the system's output** — two claims
  that share one source sentence but point in opposite directions, one affirmed and
  one flagged, copied verbatim from an actual run — plus the headline metrics up top,
  a plain-language "how it works", and an always-visible not-medical-advice notice.
  The verification page gained **one-click example claims** (the fastest way to see it
  work), a **Cancel** button, shared-link replay, a live "working" clock, a
  friendly "is the backend running?" message when the API is unreachable, and honest
  labelling ("Evidence support", not "Confidence"), with problems always listed first.

**Why this matters:** the evaluation is the centerpiece, and these two changes make
it able to carry a real claim — the decisive ablation and the significance test. The
new front end finally *shows* the product instead of only describing it.

**Next up:** scale the benchmark run (larger seeded sample, repeats, with the ablation
arm) so the significance numbers have something to bite on.

---

## 2026-07-02 — Full project audit + master improvement plan

**What got done, in plain language:**

- **Audited the whole project end to end** — the agent pipeline, the LLM layer,
  retrieval, the evaluation harness, the API, the frontend, the docs, and CI —
  checking each part against what the documents claim about it. Verdict: the
  architecture is sound and nothing needs a rewrite; all quality gates pass.
- **Found the honest gaps** and wrote them down instead of papering over them:
  the headline benchmark run is still too small to carry the thesis (20 claims,
  one pass, no true random sampling, no significance test, and no comparison
  against an *ungrounded* multi-agent setup — the exact comparison hypothesis
  H2 promises); the architecture document still describes an older pipeline
  order; and the landing/verify pages are engineering-clean but don't yet show
  the product convincingly.
- **Wrote the master improvement plan** (`docs/plans/0001-master-improvement-plan.md`):
  seventeen small, ordered work items across four workstreams — evaluation
  rigor first, documentation truth second, frontend product quality third, and
  a re-scoped Phase 5 (a reachable free-tier demo and right-sized
  observability instead of scope theater). Each item is specified precisely
  enough to be implemented independently, with its acceptance criteria.

**Why this matters:** the project's credibility rests on the evaluation being
rigorous and the documentation being true. This session converts a general
sense of "what's next" into an ordered, reviewable plan whose first priority is
making the centerpiece benchmark strong enough to carry the paper.

**Next up:** the documentation truth pass (architecture diagrams), then the
evaluation-harness hardening (seeded sampling, fault tolerance, the ablation
arm, significance), then the scaled live benchmark run.

---

## 2026-06-30 — Grew the corpus + first live benchmark numbers

**What got done, in plain language:**

- **Grew the searchable library** from a 3-document demo seed to the **full SciFact
  corpus — 5,183 real biomedical abstracts** (≈15,400 searchable passages) — loaded into
  the vector database. The system now actually has medical literature to look things up in.
- **Ran the centerpiece comparison for real, for the first time**, on the SciFact `dev`
  claims: the grounded multi-agent system vs. a single AI model, judging the *same* claims
  against the *same* retrieved evidence. The headline table in `EVALUATION.md` and the
  README is no longer a placeholder — it has live numbers.
- **The result matches the thesis.** On this first run the grounded system **caught 91.7%
  of the unsupported claims vs. 58.3%** for the single model, and **agreed with wrong claims
  far less often (16.7% vs. 41.7%)** — at about 12% more tokens and no extra latency.
- **Kept it honest.** The run is **free-tier-bounded**: 20 claims, one seeded pass, on a
  smaller model (`llama-3.1-8b-instant`) because the larger models' daily token budgets were
  used up that day. Both systems use the same model, so the comparison is fair; the writeup
  states the sample size, model, and date plainly rather than dressing it up.

**Why this matters:** this is the first evidence — measured, not asserted — that grounding
every claim in quoted evidence and surfacing disagreement actually catches more errors than
a single confident model. Scaling to the full split with repeated runs (and the stronger
model once quota resets) will tighten the numbers; the machinery to do so is already built.

**Next up:** scale the benchmark when token budget allows, then Phase 5 (production
engineering).

---

## 2026-06-30 — Phase 4: Real-time frontend

**What got done, in plain language:**

- Made the verification **visible as it happens**: the backend now streams each agent's
  result the moment it finishes (over Server-Sent Events), instead of making you wait for
  the whole pipeline to complete and returning one lump.
- Built a **live page** at `/verify` where you type a question or paste a claim and watch
  the pipeline light up stage by stage — retrieve evidence, draft the answer, check each
  claim, tally confidence, screen for safety.
- For every claim, the page shows the **verdict and the exact sentence of evidence that
  justifies it** — Supported, Contradicted, or Unverifiable — and puts every unsupported
  claim in an explicit "not supported by the evidence" callout rather than burying it.
- Showed the **confidence** (how many claims were actually backed by evidence), the
  **sources** behind the answer, and the standing **medical-advice disclaimer** up front.
- Tested it the **honest way**: the display logic is a pure piece that's checked with
  hand-built example states, and a second test drives the whole page end to end with a
  fake stream — all offline, no API key, no network.

**Why this matters:** this is the part a recruiter or mentor actually *sees*. It turns the
machinery from earlier phases into a clear, legible demonstration of the thesis — that
grounding every claim in quoted evidence, and surfacing disagreement instead of hiding it,
is what makes an answer trustworthy.

**Next up (Phase 5):** Production engineering — caching, dashboards, tracing, and a
hardened deployment.

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
