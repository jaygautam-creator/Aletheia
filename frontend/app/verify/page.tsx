"use client";

import Link from "next/link";
import { useState } from "react";

import { VerificationView } from "@/components/VerificationView";
import { useVerificationStream } from "@/lib/useVerificationStream";

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
    <main className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <Link
          href="/"
          className="font-mono text-xs tracking-widest text-neutral-500 uppercase underline-offset-4 hover:underline"
        >
          ← Aletheia
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">Live verification</h1>
        <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
          Ask a question or paste a claim. Each agent stage streams in as it completes — and every
          verdict is grounded in a quoted span of the evidence, or flagged as unsupported.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Question or claim</span>
          <textarea
            name="query"
            required
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Does aspirin reduce the risk of heart attack?"
            className="resize-y rounded-lg border border-neutral-300 bg-transparent px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none dark:border-neutral-700"
          />
        </label>

        <details className="flex flex-col gap-2">
          <summary className="cursor-pointer text-sm text-neutral-500">
            Optional: supply your own evidence and a candidate answer
          </summary>
          <div className="mt-3 flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Evidence</span>
              <span className="text-xs text-neutral-500">
                Leave blank to search the curated corpus instead.
              </span>
              <textarea
                name="evidence"
                rows={3}
                value={evidence}
                onChange={(e) => setEvidence(e.target.value)}
                className="resize-y rounded-lg border border-neutral-300 bg-transparent px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none dark:border-neutral-700"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Candidate answer</span>
              <span className="text-xs text-neutral-500">
                Leave blank to let the Generator draft one.
              </span>
              <textarea
                name="candidate_answer"
                rows={2}
                value={candidateAnswer}
                onChange={(e) => setCandidateAnswer(e.target.value)}
                className="resize-y rounded-lg border border-neutral-300 bg-transparent px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none dark:border-neutral-700"
              />
            </label>
          </div>
        </details>

        <button
          type="submit"
          disabled={streaming || !query.trim()}
          className="self-start rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-neutral-900"
        >
          {streaming ? "Verifying…" : "Verify"}
        </button>
      </form>

      <VerificationView state={state} />

      <p className="border-t border-neutral-200 pt-4 text-xs text-neutral-400 dark:border-neutral-800">
        Research tool — not medical advice. Aletheia verifies whether a claim is supported by the
        literature; it does not diagnose or treat. Consult a qualified professional.
      </p>
    </main>
  );
}
