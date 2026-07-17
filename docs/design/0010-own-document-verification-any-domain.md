# ADR 0010 — Own-document verification is any-domain

- **Status:** Accepted
- **Date:** 2026-07-17
- **Decided:** Phase 6 stretch (author-requested generalization)
- **Deciders:** Jay Gautam

## Context

The author wants Aletheia to accept claims from any field — not to feel limited
to medicine. Two locked decisions bound how that can happen:
[ADR-0001](0001-domain-focus-medical.md) focuses the *corpus* on medicine while
explicitly keeping the engine domain-agnostic, and
[ADR-0003](0003-corpus-first-hybrid-knowledge-source.md) rules out open-web
retrieval. [ADR-0009](0009-multimodal-claim-intake.md) deferred "verify against
an uploaded document" so it would not ride along inside an intake feature, and
noted that the caller-supplied `evidence` field already covers the
paste-your-own-source case.

The pipeline has accepted caller-supplied evidence end-to-end since Phase 1:
when `evidence` is present the Retriever is skipped and every verdict must
quote a span of that text. One thing blocked the "any topic" promise: the
intake guard's LLM scope classifier declined every non-medical query, even
when the caller brought the evidence — a rule written to protect the medical
corpus was being applied to requests that never touch the corpus.

## Decision

**The medical-scope rule guards the corpus, not the engine.** When the caller
supplies `evidence`, the intake guard skips the scope classifier and admits the
query — any topic may be verified against the user's own document. The
boundaries that actually matter are unchanged:

- **The injection scan always runs**, evidence or not — it is deterministic
  and runs before this carve-out.
- **The corpus path is unchanged**: with no caller evidence, the scope
  classifier still declines non-medical queries, exactly as before.
- **The verdict contract is unchanged**: verdicts against a user document must
  quote its exact words or degrade to Unverifiable, the same discipline the
  corpus path enforces.
- **The safety boundary is unchanged** ([ADR-0002](0002-verification-not-medical-advice.md)):
  the guardrail's advisory and the standing research-tool disclaimer apply to
  every response regardless of evidence source.

On the frontend, own-document verification becomes a first-class evidence-source
mode on `/verify` rather than a collapsed afterthought, the multimodal intake
chips ([ADR-0009](0009-multimodal-claim-intake.md)) can fill the document field
(the extracted text stays editable and nothing runs until the user submits),
and results grounded in a user document are labelled as such — user evidence
carries no trust tier, because it is whatever the user pasted.

## Consequences

- "Bring any claim from any genre" is now true and honest: the user brings the
  evidence, so no unbounded retrieval, no second corpus, and no new provider
  spend are involved.
- The evaluation story is untouched: the harness builds its pipelines without
  the scope guard, and every benchmark arm retrieves from the frozen corpus
  ([ADR-0006](0006-benchmark-on-fixed-corpus.md)). No headline number can move.
- A prompt-injection vector via the evidence body (a document that tries to
  instruct the Verifier) exists exactly as it did before this change — the
  evidence field has always been accepted. The Verifier treats evidence as text
  to quote, and the injection scan screens the query; hardening evidence-body
  screening further is future work if it ever matters to a measured surface.
- General-domain *benchmarking* is a separate decision: it arrives (if at all)
  as the FEVER workstream in [plan 0002](../plans/0002-generalization-plan.md),
  with its own ADR.
