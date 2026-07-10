# ADR 0009 — Multimodal claim intake is presentation-layer plumbing

- **Status:** Accepted
- **Date:** 2026-07-10
- **Decided:** after Phase 5 (demo polish, author-requested)
- **Deciders:** Jay Gautam

## Context

Claims do not always arrive as typed text: a claim may live in a paper PDF, a
screenshot or photo of a page, or be easiest to say out loud. The author asked for
PDF, image, and voice input on the verify page. The anti-drift rule this collides
with is real — features exist to be measured, and no input format moves a headline
metric. The resolution is to make intake **strictly a convenience for producing the
text** the existing pipeline already accepts, with a boundary tight enough that the
measured system is provably unchanged.

Two harder versions were considered and rejected:

- **Auto-verify on upload** (extract, then immediately run the pipeline). Rejected:
  extraction can mishear speech or misread an image, and a verdict on a mis-heard
  claim looks like a verdict on the user's claim. The user must see and confirm the
  text first — the same review-before-verify posture the rest of the UI takes.
- **Multimodal evidence** (verify *against* an uploaded document). Deferred: it
  touches the grounding path and the evaluation story, so it must not ride along in
  an intake feature. The caller-supplied `evidence` field already covers the
  paste-your-own-source case.

## Decision

One new endpoint, `POST /extract`, that turns **one uploaded file into plain text**
and does nothing else. The frontend places the returned text into the *editable*
query field; the user reviews it and presses Verify themselves. The verification
pipeline, the verdict contract, and the evaluation harness are untouched.

Free-tier extraction per media kind, reusing keys already in `.env`:

| Kind | Types | Extractor |
| --- | --- | --- |
| PDF | `application/pdf` | `pypdf` text layer (no key, offline) |
| Image | PNG / JPEG / WebP | Gemini vision (`VISION_MODEL`, reuses `GEMINI_API_KEY`) |
| Voice | webm / ogg / mp3 / mp4 / m4a / wav / flac | Groq Whisper (`TRANSCRIPTION_MODEL`, reuses `GROQ_API_KEY`) |

Boundary rules that keep the route honest:

- **In memory only.** Uploads are read, extracted, and discarded — never written to
  disk, the corpus, or the database. Nothing an upload contains can enter the
  evidence pool.
- **Same guardrails as `/verify`.** `/extract` spends the shared providers' budget,
  so it sits behind the same per-IP rate-limit bucket; it gets its own, larger body
  cap (`MAX_UPLOAD_BYTES`, default 10 MiB) while every JSON route keeps the strict
  quarter-megabyte cap.
- **A claim, not a document dump.** Extractions are truncated to
  `EXTRACT_MAX_CHARS` (default 4,000) with an explicit `truncated` flag the UI
  surfaces — the target of the query field is a claim to check, and the intake
  guard still screens whatever is submitted.
- **Failures name whose problem they are.** An unreadable/illegible/silent upload
  is a 422 (the file), a provider failure is a 502 (upstream), a missing key is a
  503 naming the variable — and a missing Gemini key must not break PDF extraction,
  which needs no key at all.
- **Browser recording stays modest.** The mic capture auto-stops at 60 seconds and
  falls back to a plain audio-file picker where `MediaRecorder` is unavailable.

## Consequences

- The demo meets people where their claims actually are, at zero marginal
  infrastructure: two new pure-Python/SDK calls, no storage, no queue.
- The paper's evaluation story is unaffected — the harness never touches
  `/extract`, and no benchmark number depends on it.
- Extraction quality is deliberately unmeasured (it is not a claim about the
  thesis). If intake errors ever matter — e.g. voice claims mis-transcribed often
  enough to mislead users — that becomes its own measured feature with its own
  dataset, per the anti-drift decision rule.
- General-domain ("all genres") verification remains out of scope
  ([ADR-0001](0001-domain-focus-medical.md)); intake changes how a claim *arrives*,
  not what corpus it is judged against.
