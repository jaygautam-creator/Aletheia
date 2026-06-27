# ADR 0002 — Aletheia verifies claims; it never gives medical advice

- **Status:** Accepted (locked) — **hard non-negotiable**
- **Date:** 2026-06-27
- **Decided:** ahead of Phase 2 (Retrieval & grounding)
- **Deciders:** Jay Gautam

## Context

Operating in the medical domain ([ADR-0001](0001-domain-focus-medical.md)) carries a
safety obligation that does not exist for, say, trivia. A system that emits fluent
medical text can be *read* as medical advice even when that is not its job — and acting
on wrong medical advice causes real harm (`PROJECT_CHARTER.md` §2). The boundary must be
explicit, structural, and visible to the user, not left to good intentions.

## Decision

Aletheia is a **claim-verification research tool, not a medical advisor.**

- It verifies whether a **claim** is `Supported`, `Contradicted`, or `Unverifiable`
  *relative to retrieved evidence*. That is the entire output contract
  (`backend/src/aletheia/agents/contracts.py`).
- It must **never** provide medical advice, diagnosis, treatment recommendations,
  dosing, or any individualized clinical guidance. It does not answer *"what should I
  do"*; it assesses *"is this claim supported by the literature."*
- A clear, prominent disclaimer — **"Research tool — not medical advice. Consult a
  qualified professional."** — must appear in:
  - the **UI**, persistently (not buried in a footer);
  - **every API response** that returns a verdict; and
  - the **README**.
- This is recorded as a **hard non-negotiable** in `ANTI_DRIFT.md`'s out-of-scope list:
  *never generate medical advice/diagnosis.*

## Consequences

- **The verdict contract is the safety boundary.** Because the system can only emit
  grounded verdicts *about a stated claim* — and downgrades anything it cannot ground to
  `Unverifiable` — it structurally avoids free-form advice. The Generator decomposes and
  the Verifier judges against evidence; neither prescribes.
- The disclaimer is threaded into the **API response schema** in Phase 2 and into the
  **UI** in Phase 4. These are tracked as phase tasks, not optional polish.
- The Phase 2 **guardrail layer** is designed to refuse the reframing of the tool as an
  advice channel: an advice-seeking input ("what should I take for X") is handled as the
  verification of a stated claim, or declined — never answered as advice.
- Confidence describes *evidence strength*, not clinical certainty
  ([ADR-0005](0005-confidence-from-evidence.md)).

## Related

- `ANTI_DRIFT.md` — out-of-scope hard non-negotiable.
- [ADR-0001](0001-domain-focus-medical.md) (medical domain), [ADR-0005](0005-confidence-from-evidence.md) (confidence is about evidence).
