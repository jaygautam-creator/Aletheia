"use client";

import { useEffect, useState } from "react";

import { elapsedSeconds, wakeMessage, wakeProgress, type WakeStatus } from "@/lib/wake";

/**
 * Disclose a free-tier cold start instead of hanging on an unlabelled spinner.
 *
 * Renders nothing when the backend answered promptly (the common case). On a cold start it
 * explains what is happening, counts the wait, and creeps a progress bar so the page reads
 * as "starting", not "broken" — then confirms and retires itself once the API answers.
 */
export function BackendWaking({
  status,
  elapsedMs,
  onRetry,
}: {
  status: WakeStatus;
  elapsedMs: number;
  onRetry: () => void;
}) {
  const [dismissed, setDismissed] = useState(false);

  // The "ready" confirmation is a beat of reassurance, not a permanent banner: a visitor
  // who waited deserves to see it resolve, then get the page back.
  useEffect(() => {
    if (status !== "ready") return;
    const id = setTimeout(() => setDismissed(true), 2600);
    return () => clearTimeout(id);
  }, [status]);

  if (status === "unknown" || status === "awake") return null;
  if (status === "ready" && dismissed) return null;

  if (status === "unreachable") {
    return (
      <div
        role="status"
        className="glass flex flex-col gap-3 rounded-3xl border-l-2 border-l-amber-400 p-5"
      >
        <p className="font-mono text-[10px] tracking-widest text-amber-700 uppercase">
          backend unreachable
        </p>
        <p className="text-sm leading-relaxed text-slate-600">
          The demo API isn&rsquo;t responding. It runs on a free instance that may be asleep or
          restarting — the verification path needs it, but the{" "}
          <a href="/benchmark" className="text-teal-700 underline decoration-teal-300">
            benchmark results
          </a>{" "}
          are served from this page and still work.
        </p>
        <button
          type="button"
          onClick={() => {
            setDismissed(false);
            onRetry();
          }}
          className="self-start rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs text-slate-600 transition hover:border-teal-300 hover:text-teal-700"
        >
          Try again
        </button>
      </div>
    );
  }

  const ready = status === "ready";
  const progress = ready ? 1 : wakeProgress(elapsedMs);
  const seconds = elapsedSeconds(elapsedMs);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`glass flex flex-col gap-3 rounded-3xl border-l-2 p-5 transition-colors ${
        ready ? "border-l-teal-500" : "border-l-cyan-400"
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p
          className={`font-mono text-[10px] tracking-widest uppercase ${
            ready ? "text-teal-700" : "text-cyan-700"
          }`}
        >
          {ready ? "server ready" : "starting the demo server"}
        </p>
        {!ready && (
          <span className="font-mono text-xs text-slate-400 tabular-nums">{seconds}s</span>
        )}
      </div>

      <p className="text-sm leading-relaxed text-slate-700">
        {ready ? "The backend is up — verification is ready to run." : wakeMessage(elapsedMs)}
      </p>

      {!ready && (
        <p className="text-xs leading-relaxed text-slate-500">
          Aletheia&rsquo;s API runs on a free instance that sleeps when idle, so the first visit
          after a quiet spell waits about a minute while it boots and loads the retrieval model.
          Every visit after this one is immediate.
        </p>
      )}

      {/* Determinate-looking but honest: the fill is paced by elapsed time and capped
          below full until the API actually answers (see wakeProgress). A CSS width
          transition is the only motion, so reduced-motion users lose nothing. */}
      <div
        className="h-1 w-full overflow-hidden rounded-full bg-slate-900/10"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress * 100)}
        aria-label="Backend startup progress"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${
            ready ? "bg-teal-500" : "bg-gradient-to-r from-teal-500 to-cyan-400"
          }`}
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </div>
  );
}
