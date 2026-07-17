"use client";

import { useEffect, useRef, useState } from "react";

import { ClaimIntake } from "@/components/ClaimIntake";
import { VerificationView } from "@/components/VerificationView";
import { useVerificationStream } from "@/lib/useVerificationStream";

const FIELD =
  "resize-y rounded-xl border border-slate-300/70 bg-white/70 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 focus:outline-none";

// Curated one-click examples. Each is chosen to show a distinct outcome against the
// frozen corpus so a first-time visitor sees the range of the system in a few clicks.
const EXAMPLES: readonly { label: string; query: string; note: string }[] = [
  {
    label: "A supported claim",
    query: "ALDH1 expression is associated with poorer prognosis in breast cancer.",
    note: "grounded → Supported",
  },
  {
    label: "A wrong-direction claim",
    query: "ALDH1 expression is associated with better breast cancer outcomes.",
    note: "the evidence disagrees → Contradicted",
  },
  {
    label: "Outside the corpus",
    query: "Albendazole is used to treat lymphatic filariasis.",
    note: "no evidence found → Unverifiable",
  },
  {
    label: "Out of scope",
    query: "Write Python code for a star pattern.",
    note: "declined by the intake guard",
  },
];

// Own-document examples (ADR-0010): any topic works when the user brings the evidence.
// Each pairs a claim with a short document so one click shows the mode end-to-end.
const DOC_EXAMPLES: readonly {
  label: string;
  query: string;
  evidence: string;
  note: string;
}[] = [
  {
    label: "A history claim",
    query: "The Eiffel Tower opened to the public in 1889.",
    evidence:
      "The Eiffel Tower was built as the entrance arch to the 1889 World's Fair in Paris. " +
      "Construction finished in March 1889, and the tower opened to the public on 15 May 1889. " +
      "At 300 metres it was the tallest structure in the world at the time.",
    note: "the document confirms it → Supported",
  },
  {
    label: "A claim the document contradicts",
    query: "The first modern Olympic Games were held in Paris.",
    evidence:
      "The first modern Olympic Games were held in Athens, Greece, in April 1896. " +
      "Paris hosted the second Games in 1900, where women competed for the first time.",
    note: "the document disagrees → Contradicted",
  },
];

function ShareButton({ query, disabled }: { query: string; disabled: boolean }) {
  const [copied, setCopied] = useState(false);

  function share() {
    const url = new URL(window.location.href);
    url.searchParams.set("q", query);
    history.pushState(null, "", url.toString());
    void navigator.clipboard.writeText(url.toString()).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      type="button"
      onClick={share}
      disabled={disabled || !query.trim()}
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-4 py-3 text-sm text-slate-600 shadow-sm backdrop-blur-sm transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {copied ? "✓ Link copied" : "Share"}
    </button>
  );
}

export default function VerifyPage() {
  const { state, start, cancel } = useVerificationStream();
  const [query, setQuery] = useState("");
  const [evidenceMode, setEvidenceMode] = useState<"corpus" | "document">("corpus");
  const [evidence, setEvidence] = useState("");
  const [candidateAnswer, setCandidateAnswer] = useState("");
  const [ranWithEvidence, setRanWithEvidence] = useState(false);
  const autoRan = useRef(false);

  const streaming = state.status === "streaming";
  const documentMode = evidenceMode === "document";

  // `nextEvidence` lets one-click document examples run before setState lands; otherwise
  // the active mode decides whether the evidence field rides along (ADR-0010: with a
  // document, any topic; without one, the corpus and its medical scope).
  function run(nextQuery: string, nextEvidence?: string) {
    const trimmed = nextQuery.trim();
    if (!trimmed) return;
    const doc = (nextEvidence ?? (documentMode ? evidence : "")).trim();
    setRanWithEvidence(Boolean(doc));
    void start({
      query: trimmed,
      evidence: doc || undefined,
      candidate_answer: candidateAnswer.trim() || undefined,
    });
  }

  // A shared ?q= link replays the verification: fill the field and run once, on mount.
  // Deferred to a macrotask so the initial (SSR-matching) render commits first — reading
  // window and dispatching happen off the render path.
  useEffect(() => {
    if (autoRan.current) return;
    autoRan.current = true;
    const shared = new URLSearchParams(window.location.search).get("q");
    if (!shared) return;
    const id = setTimeout(() => {
      setQuery(shared);
      run(shared);
    }, 0);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onExample(exampleQuery: string) {
    setQuery(exampleQuery);
    run(exampleQuery);
  }

  function onDocumentExample(exampleQuery: string, exampleEvidence: string) {
    setQuery(exampleQuery);
    setEvidence(exampleEvidence);
    run(exampleQuery, exampleEvidence);
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (streaming) return;
    run(query);
  }

  function onQueryKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-10 px-6 pt-16 pb-28">
      <header className="animate-fade-up flex flex-col gap-3">
        <p className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
          live verification
        </p>
        <h1 className="font-serif text-4xl font-medium tracking-tight text-slate-900">
          Verify a claim against the evidence
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
          Ask a question or paste a claim — or bring your own document and check a claim from any
          field against it. Each agent stage streams in as it completes, and every verdict is
          grounded in a quoted span of the evidence, or flagged as unsupported.
        </p>
      </header>

      <form
        onSubmit={onSubmit}
        className="glass animate-fade-up flex flex-col gap-4 rounded-3xl p-6"
        style={{ animationDelay: "0.08s" }}
      >
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-800">Question or claim</span>
          <textarea
            name="query"
            required
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onQueryKeyDown}
            placeholder="Does aspirin reduce the risk of heart attack?"
            className={FIELD}
          />
        </label>

        {/* Multimodal intake — extraction fills the *editable* field above (the claim) or
            below (the document) for review; nothing is verified until the user submits
            (ADR-0009). */}
        {!documentMode && <ClaimIntake disabled={streaming} onText={setQuery} />}

        {/* Evidence source (ADR-0010): the curated corpus is medical; with your own
            document, any topic works — verdicts quote that document or say "can't tell". */}
        <div className="flex flex-col gap-2" role="radiogroup" aria-label="Evidence source">
          <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">
            Check against
          </span>
          <div className="flex flex-wrap gap-2">
            {(
              [
                { mode: "corpus", label: "The curated corpus", hint: "medical literature" },
                { mode: "document", label: "My own document", hint: "any topic" },
              ] as const
            ).map((option) => (
              <button
                key={option.mode}
                type="button"
                role="radio"
                aria-checked={evidenceMode === option.mode}
                onClick={() => setEvidenceMode(option.mode)}
                disabled={streaming}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  evidenceMode === option.mode
                    ? "border-teal-400 bg-teal-50 font-medium text-teal-800"
                    : "border-slate-200 bg-white/60 text-slate-600 hover:border-teal-300 hover:text-teal-700"
                }`}
              >
                {option.label}
                <span
                  className={evidenceMode === option.mode ? "text-teal-500" : "text-slate-400"}
                >
                  · {option.hint}
                </span>
              </button>
            ))}
          </div>
        </div>

        {documentMode && (
          <>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-800">Your document</span>
              <span className="text-xs text-slate-500">
                Any topic — verdicts will quote this text verbatim, or say it can&rsquo;t tell.
              </span>
              <textarea
                name="evidence"
                rows={6}
                value={evidence}
                onChange={(e) => setEvidence(e.target.value)}
                placeholder="Paste the passage, article, or report to check the claim against."
                className={FIELD}
              />
            </label>
            <ClaimIntake
              disabled={streaming}
              onText={setEvidence}
              label="Or bring the document as a file"
            />
          </>
        )}

        {/* One-click examples — the fastest path to seeing the active mode work */}
        <div className="flex flex-col gap-2">
          <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">
            Try an example
          </span>
          <div className="flex flex-wrap gap-2">
            {!documentMode &&
              EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  type="button"
                  onClick={() => onExample(ex.query)}
                  disabled={streaming}
                  title={ex.note}
                  className="group flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1.5 text-xs text-slate-600 transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {ex.label}
                  <span className="text-slate-300 transition group-hover:text-teal-400">→</span>
                </button>
              ))}
            {documentMode &&
              DOC_EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  type="button"
                  onClick={() => onDocumentExample(ex.query, ex.evidence)}
                  disabled={streaming}
                  title={ex.note}
                  className="group flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1.5 text-xs text-slate-600 transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {ex.label}
                  <span className="text-slate-300 transition group-hover:text-teal-400">→</span>
                </button>
              ))}
          </div>
        </div>

        <details className="flex flex-col gap-2">
          <summary className="cursor-pointer text-sm text-slate-500 transition-colors hover:text-slate-800">
            Optional: supply a candidate answer
          </summary>
          <div className="mt-3 flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-800">Candidate answer</span>
              <span className="text-xs text-slate-500">
                Leave blank to let the Generator draft one.
              </span>
              <textarea
                name="candidate_answer"
                rows={2}
                value={candidateAnswer}
                onChange={(e) => setCandidateAnswer(e.target.value)}
                className={FIELD}
              />
            </label>
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-3">
          {streaming ? (
            <button
              type="button"
              onClick={cancel}
              className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-white/70 px-6 py-3 text-sm font-medium text-rose-600 shadow-sm transition hover:border-rose-300 hover:bg-rose-50"
            >
              Cancel
            </button>
          ) : (
            <button
              type="submit"
              disabled={!query.trim() || (documentMode && !evidence.trim())}
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-teal-600 to-cyan-500 px-6 py-3 text-sm font-medium text-white shadow-[0_10px_30px_-10px_rgba(13,148,136,0.6)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
            >
              Verify
            </button>
          )}
          {/* A shared ?q= link replays against the corpus, so sharing is corpus-mode only. */}
          {!documentMode && <ShareButton query={query} disabled={streaming} />}
          {!streaming && query.trim() && (
            <span className="font-mono text-xs text-slate-400">⌘↵ to submit</span>
          )}
        </div>
      </form>

      <VerificationView state={state} userEvidence={ranWithEvidence} />

      <p className="border-t border-slate-900/10 pt-4 text-xs leading-relaxed text-slate-400">
        Research tool — not medical advice. Aletheia verifies whether a claim is supported by the
        evidence; it does not diagnose or treat. Consult a qualified professional.
      </p>
    </main>
  );
}
