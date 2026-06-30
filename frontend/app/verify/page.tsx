"use client";

import { useState } from "react";

import { VerificationView } from "@/components/VerificationView";
import { useVerificationStream } from "@/lib/useVerificationStream";

const FIELD =
  "resize-y rounded-xl border border-slate-300/70 bg-white/70 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 focus:outline-none";

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
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-10 px-6 pt-16 pb-28">
      <header className="animate-fade-up flex flex-col gap-3">
        <p className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
          live verification
        </p>
        <h1 className="font-serif text-4xl font-medium tracking-tight text-slate-900">
          Verify a claim against the evidence
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
          Ask a question or paste a claim. Each agent stage streams in as it completes — and every
          verdict is grounded in a quoted span of the evidence, or flagged as unsupported.
        </p>
      </header>

      <form
        onSubmit={onSubmit}
        className="animate-fade-up flex flex-col gap-4 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-[0_24px_70px_-40px_rgba(12,27,42,0.4)] backdrop-blur-xl"
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
            placeholder="Does aspirin reduce the risk of heart attack?"
            className={FIELD}
          />
        </label>

        <details className="flex flex-col gap-2">
          <summary className="cursor-pointer text-sm text-slate-500 transition-colors hover:text-slate-800">
            Optional: supply your own evidence and a candidate answer
          </summary>
          <div className="mt-3 flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-800">Evidence</span>
              <span className="text-xs text-slate-500">
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

        <button
          type="submit"
          disabled={streaming || !query.trim()}
          className="inline-flex items-center gap-2 self-start rounded-full bg-gradient-to-r from-teal-600 to-cyan-500 px-6 py-3 text-sm font-medium text-white shadow-[0_10px_30px_-10px_rgba(13,148,136,0.6)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          {streaming ? "Verifying…" : "Verify"}
        </button>
      </form>

      <VerificationView state={state} />

      <p className="border-t border-slate-900/10 pt-4 text-xs leading-relaxed text-slate-400">
        Research tool — not medical advice. Aletheia verifies whether a claim is supported by the
        literature; it does not diagnose or treat. Consult a qualified professional.
      </p>
    </main>
  );
}
