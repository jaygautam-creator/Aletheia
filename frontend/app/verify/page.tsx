"use client";

import { useState } from "react";

import { VerificationView } from "@/components/VerificationView";
import { useVerificationStream } from "@/lib/useVerificationStream";

const FIELD =
  "resize-y rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-600 transition-colors focus:border-emerald-400/60 focus:ring-1 focus:ring-emerald-400/25 focus:outline-none";

export default function VerifyPage() {
  const { state, start } = useVerificationStream();
  const [query, setQuery] = useState("");
  const [evidence, setEvidence] = useState("");
  const [candidateAnswer, setCandidateAnswer] = useState("");

  const streaming = state.status === "streaming";

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || streaming) return;
    void start({
      query: trimmed,
      evidence: evidence.trim() || undefined,
      candidate_answer: candidateAnswer.trim() || undefined,
    });
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-10 px-6 pt-16 pb-24">
      <header className="flex flex-col gap-3">
        <p className="font-mono text-xs tracking-[0.25em] text-emerald-400/90 uppercase">
          live verification
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-50">
          Verify a claim against the evidence
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-neutral-400">
          Ask a question or paste a claim. Each agent stage streams in as it completes — and every
          verdict is grounded in a quoted span of the evidence, or flagged as unsupported.
        </p>
      </header>

      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-4 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5 shadow-[0_12px_40px_-20px_rgba(0,0,0,0.8)]"
      >
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-neutral-200">Question or claim</span>
          <textarea
            name="query"
            required
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Does aspirin reduce the risk of heart attack?"
            className={FIELD}
          />
        </label>

        <details className="flex flex-col gap-2">
          <summary className="cursor-pointer text-sm text-neutral-500 transition-colors hover:text-neutral-300">
            Optional: supply your own evidence and a candidate answer
          </summary>
          <div className="mt-3 flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-neutral-200">Evidence</span>
              <span className="text-xs text-neutral-500">
                Leave blank to search the curated corpus instead.
              </span>
              <textarea
                name="evidence"
                rows={3}
                value={evidence}
                onChange={(e) => setEvidence(e.target.value)}
                className={FIELD}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-neutral-200">Candidate answer</span>
              <span className="text-xs text-neutral-500">
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

        <button
          type="submit"
          disabled={streaming || !query.trim()}
          className="inline-flex items-center gap-2 self-start rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-medium text-neutral-950 shadow-[0_0_24px_-6px_rgba(16,185,129,0.7)] transition hover:bg-emerald-400 hover:shadow-[0_0_32px_-4px_rgba(16,185,129,0.9)] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          {streaming ? "Verifying…" : "Verify"}
        </button>
      </form>

      <VerificationView state={state} />

      <p className="border-t border-white/[0.08] pt-4 text-xs leading-relaxed text-neutral-500">
        Research tool — not medical advice. Aletheia verifies whether a claim is supported by the
        literature; it does not diagnose or treat. Consult a qualified professional.
      </p>
    </main>
  );
}
