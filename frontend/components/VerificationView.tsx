"use client";

// Presentational view for the streamed verification path.
//
// It renders a `StreamState` (produced by useVerificationStream) and is intentionally
// pure — no network calls — so it can be unit-tested with crafted states. The route
// at app/verify wires the hook's live state into this component.

import { useEffect, useState } from "react";

import type { Advisory, Citation, ClaimVerdict, StreamState, Verdict } from "@/lib/verification";

// Flagged verdicts first (Contradicted, then Unverifiable, then Supported) so the reader's
// eye hits the problems before the confirmations (ADR-0004: surface disagreement).
const VERDICT_ORDER: Record<Verdict, number> = { Contradicted: 0, Unverifiable: 1, Supported: 2 };

function flaggedFirst(verdicts: ClaimVerdict[]): ClaimVerdict[] {
  return [...verdicts].sort((a, b) => VERDICT_ORDER[a.verdict] - VERDICT_ORDER[b.verdict]);
}

/** A live seconds counter shown while the pipeline streams, so slow calls read as "working". */
function StreamClock({ startedAt }: { startedAt: number | null }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(id);
  }, []);
  if (startedAt == null) return null;
  return (
    <span className="font-mono text-xs text-slate-400 tabular-nums">
      {((now - startedAt) / 1000).toFixed(1)}s
    </span>
  );
}

/** Recognise a connection failure (backend unreachable) vs a server-reported error. */
function isConnectionError(message: string): boolean {
  const m = message.toLowerCase();
  return (
    m.includes("failed to fetch") ||
    m.includes("networkerror") ||
    m.includes("load failed") ||
    (m.includes("request failed") && !/http\s*\d/.test(m))
  );
}

const CANONICAL_STAGES = [
  { id: "retriever", label: "Retriever", detail: "hybrid evidence search" },
  { id: "generator", label: "Generator", detail: "answer + atomic claims" },
  { id: "verifier", label: "Verifier", detail: "verdict + quoted span" },
  { id: "aggregator", label: "Aggregator", detail: "answer · confidence · disagreements" },
  { id: "guardrail", label: "Guardrail", detail: "advisory + disclaimer" },
] as const;

type StageState = "pending" | "active" | "done" | "skipped";

function stageState(id: string, stages: string[], streaming: boolean): StageState {
  const arrivedAt = stages.indexOf(id);
  if (arrivedAt !== -1) {
    const isLatest = arrivedAt === stages.length - 1;
    return isLatest && streaming ? "active" : "done";
  }
  // Not arrived: a later canonical stage having run means this one was skipped
  // (the Retriever is skipped when the caller supplies their own evidence).
  const order = CANONICAL_STAGES.findIndex((s) => s.id === id);
  const laterRan = stages.some((s) => CANONICAL_STAGES.findIndex((c) => c.id === s) > order);
  return laterRan ? "skipped" : "pending";
}

function stageSummary(id: string, state: StreamState): string | null {
  if (!state.stages.includes(id)) return null;
  switch (id) {
    case "retriever": {
      const n = state.citations.length;
      return `Retrieved ${n} source${n !== 1 ? "s" : ""}`;
    }
    case "generator": {
      const n = state.claims.length;
      return n > 0 ? `Generated ${n} claim${n !== 1 ? "s" : ""}` : null;
    }
    case "verifier": {
      const total = state.verdicts.length;
      if (total === 0) return null;
      const supported = state.verdicts.filter((v) => v.verdict === "Supported").length;
      return `${supported}/${total} supported`;
    }
    case "aggregator": {
      if (!state.result) return null;
      const pct = Math.round(state.result.support_ratio * 100);
      return `${pct}% supported`;
    }
    case "guardrail":
      return state.safety ? state.safety.advisory.replace("_", " ") : null;
    default:
      return null;
  }
}

const STAGE_DOT: Record<StageState, string> = {
  done: "bg-teal-500 shadow-[0_0_8px_1px_rgba(20,184,166,0.5)]",
  active: "bg-cyan-500 animate-pulse shadow-[0_0_10px_2px_rgba(6,182,212,0.6)]",
  skipped: "bg-slate-300",
  pending: "bg-slate-200",
};

const VERDICT_STYLE: Record<Verdict, string> = {
  Supported: "border-teal-300 bg-teal-50 text-teal-800",
  Contradicted: "border-rose-300 bg-rose-50 text-rose-700",
  Unverifiable: "border-amber-300 bg-amber-50 text-amber-800",
};

const ADVISORY_STYLE: Record<Advisory, string> = {
  info: "border-sky-300 bg-sky-50 text-sky-900",
  caution: "border-amber-300 bg-amber-50 text-amber-900",
  high_caution: "border-rose-300 bg-rose-50 text-rose-900",
};

const ADVISORY_LABEL: Record<Advisory, string> = {
  info: "Advisory",
  caution: "Caution",
  high_caution: "High caution",
};

const CARD = "glass rounded-2xl";

function PipelineProgress({ state }: { state: StreamState }) {
  const streaming = state.status === "streaming";
  return (
    <ol aria-label="Verification pipeline" className="flex flex-col gap-1.5">
      {CANONICAL_STAGES.map((stage) => {
        const status = stageState(stage.id, state.stages, streaming);
        const summary = stageSummary(stage.id, state);
        const elapsed = state.startedAt != null ? state.stageTimes[stage.id] : undefined;
        const timeLabel = elapsed != null ? `${(elapsed / 1000).toFixed(1)}s` : null;
        return (
          <li
            key={stage.id}
            aria-current={status === "active" ? "step" : undefined}
            className="flex items-center gap-3 text-sm"
            data-testid={`stage-${stage.id}`}
            data-state={status}
          >
            <span aria-hidden className={`h-2.5 w-2.5 shrink-0 rounded-full ${STAGE_DOT[status]}`} />
            <span
              className={
                status === "pending" || status === "skipped"
                  ? "text-slate-400"
                  : "font-medium text-slate-900"
              }
            >
              {stage.label}
            </span>
            <span className="text-xs text-slate-500">{stage.detail}</span>
            {status === "skipped" && (
              <span className="font-mono text-[10px] tracking-wide text-slate-400 uppercase">
                skipped
              </span>
            )}
            {summary && (
              <span className="ml-auto text-xs text-slate-500">{summary}</span>
            )}
            {timeLabel && status === "done" && (
              <span className="font-mono text-[10px] text-slate-400">{timeLabel}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function SafetyBanner({ state }: { state: StreamState }) {
  const safety = state.safety;
  if (!safety) return null;
  return (
    <div
      role="note"
      className={`flex flex-col gap-2 rounded-2xl border px-4 py-3 text-sm ${ADVISORY_STYLE[safety.advisory]}`}
    >
      <p className="font-medium">{ADVISORY_LABEL[safety.advisory]}</p>
      <p>{safety.disclaimer}</p>
      {safety.notes.length > 0 && (
        <ul className="list-disc pl-5 text-xs opacity-90">
          {safety.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Confidence({ verdicts, ratio }: { verdicts: ClaimVerdict[]; ratio: number | null }) {
  if (verdicts.length === 0) return null;
  const supported = verdicts.filter((v) => v.verdict === "Supported").length;
  const pct =
    ratio === null ? Math.round((supported / verdicts.length) * 100) : Math.round(ratio * 100);

  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct / 100);

  return (
    <div className={`flex items-center gap-5 ${CARD} p-5`}>
      <div
        role="meter"
        aria-label="Share of claims supported by evidence"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="relative h-[84px] w-[84px] shrink-0"
      >
        <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90" aria-hidden>
          <circle cx="40" cy="40" r={radius} className="fill-none stroke-slate-200" strokeWidth="8" />
          <circle
            cx="40"
            cy="40"
            r={radius}
            className="fill-none transition-[stroke-dashoffset] duration-700 ease-out"
            stroke="url(#confGrad)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
          <defs>
            <linearGradient id="confGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#0d9488" />
              <stop offset="100%" stopColor="#22d3ee" />
            </linearGradient>
          </defs>
        </svg>
        <span className="absolute inset-0 grid place-items-center text-lg font-semibold text-slate-900 tabular-nums">
          {pct}%
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="font-mono text-xs tracking-widest text-slate-400 uppercase">
          Evidence support
        </span>
        <span className="text-sm text-slate-600">
          {supported} of {verdicts.length} claims grounded in evidence
        </span>
      </div>
    </div>
  );
}

const REASONING_THRESHOLD = 140;

function ClaimCard({ verdict }: { verdict: ClaimVerdict }) {
  const isLong = (verdict.reasoning?.length ?? 0) > REASONING_THRESHOLD;
  const [expanded, setExpanded] = useState(!isLong);

  function toggle() {
    setExpanded((p) => !p);
  }

  return (
    <li className={`flex flex-col gap-2 ${CARD} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-900">{verdict.claim}</p>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${VERDICT_STYLE[verdict.verdict]}`}
        >
          {verdict.verdict}
        </span>
      </div>
      {verdict.quoted_span && (
        <blockquote className="border-l-2 border-teal-400 pl-3 text-sm text-slate-600 italic">
          &ldquo;{verdict.quoted_span}&rdquo;
        </blockquote>
      )}
      {verdict.reasoning && (
        <>
          <p className={`text-xs text-slate-500 ${!expanded ? "line-clamp-2" : ""}`}>
            {verdict.reasoning}
          </p>
          {isLong && (
            <button
              type="button"
              onClick={toggle}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggle();
                }
              }}
              className="self-start text-xs text-teal-600 transition-colors hover:text-teal-800"
            >
              {expanded ? "Show less ↑" : "Show more ↓"}
            </button>
          )}
        </>
      )}
    </li>
  );
}

function Disagreements({ verdicts }: { verdicts: ClaimVerdict[] }) {
  const flagged = flaggedFirst(verdicts.filter((v) => v.verdict !== "Supported"));
  if (flagged.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-rose-200 bg-rose-50/80 px-4 py-3 backdrop-blur-md">
      <p className="text-sm font-medium text-rose-800">
        {flagged.length} {flagged.length === 1 ? "claim is" : "claims are"} not supported by the
        evidence
      </p>
      <ul className="flex flex-col gap-1 text-sm text-rose-700">
        {flagged.map((v) => (
          <li key={v.claim}>
            <span className="font-medium">{v.verdict}:</span> {v.claim}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <section aria-labelledby="citations-heading" className="flex flex-col gap-2">
      <h3
        id="citations-heading"
        className="font-mono text-xs tracking-widest text-slate-400 uppercase"
      >
        Sources
      </h3>
      <ol className="flex flex-col gap-1.5">
        {citations.map((c) => (
          <li key={c.index} className="flex gap-2 text-sm">
            <span className="font-mono text-slate-400">[{c.index}]</span>
            <span className="flex flex-col">
              {c.url ? (
                <a
                  href={c.url}
                  className="text-slate-800 underline-offset-4 transition-colors hover:text-teal-700 hover:underline"
                  rel="noreferrer"
                  target="_blank"
                >
                  {c.title}
                </a>
              ) : (
                <span className="text-slate-800">{c.title}</span>
              )}
              <span className="font-mono text-xs text-slate-400">
                {c.connector} · {c.trust_tier} · {c.score.toFixed(2)}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard access denied — silently no-op
    }
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      className="rounded-full border border-slate-200 bg-white/60 px-2.5 py-0.5 font-mono text-[10px] tracking-wide text-slate-400 uppercase transition-colors hover:border-teal-300 hover:text-teal-600"
      aria-label="Copy answer to clipboard"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

export function VerificationView({ state }: { state: StreamState }) {
  if (state.status === "idle") {
    return (
      <p className="text-sm text-slate-500" data-testid="idle-hint">
        Enter a claim or question and run the verifier — each agent stage will stream in as it
        completes.
      </p>
    );
  }

  // The aggregator's assembled result is authoritative once present; before then, fall back
  // to the partials streamed by the generator and verifier so the view fills in live.
  const answer = state.result?.candidate_answer ?? state.candidateAnswer;
  const verdicts = state.result?.verdicts ?? state.verdicts;
  const ratio = state.result?.support_ratio ?? null;
  // The intake guard declined the query (out of scope or a blocked injection attempt):
  // there is no answer to show, so the view becomes the decline notice plus the advisory.
  const refused = state.result?.refused === true;

  return (
    <div className="flex flex-col gap-6">
      <div
        role="status"
        aria-live="polite"
        aria-busy={state.status === "streaming"}
        className={`flex flex-col gap-3 ${CARD} p-5`}
      >
        <span className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs tracking-widest text-slate-400 uppercase">
            {state.status === "streaming" ? "Verifying…" : "Pipeline"}
          </span>
          {state.status === "streaming" && <StreamClock startedAt={state.startedAt} />}
        </span>
        <PipelineProgress state={state} />
      </div>

      {state.status === "error" && (
        <div
          role="alert"
          className="flex flex-col gap-1 rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          {state.error && isConnectionError(state.error) ? (
            <>
              <span className="font-medium">The verification API isn&rsquo;t reachable.</span>
              <span className="text-rose-600">
                Is the backend running? Start it with{" "}
                <code className="rounded bg-rose-100 px-1 py-0.5 font-mono text-xs">make dev</code>,
                then try again.
              </span>
            </>
          ) : (
            (state.error ?? "Something went wrong.")
          )}
        </div>
      )}

      {refused && (
        <div
          data-testid="refusal"
          className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50/80 px-5 py-4 backdrop-blur-md"
        >
          <span aria-hidden className="mt-0.5 text-lg">
            ⚠
          </span>
          <div className="flex flex-col gap-1">
            <p className="font-serif text-lg font-medium text-amber-900">Request declined</p>
            <p className="text-sm leading-relaxed text-amber-800">
              {state.result?.refusal_reason ??
                "This request is outside Aletheia's scope. Aletheia only verifies medical and health-related claims."}
            </p>
          </div>
        </div>
      )}

      {answer && (
        <section aria-labelledby="answer-heading" className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <h3
              id="answer-heading"
              className="font-mono text-xs tracking-widest text-slate-400 uppercase"
            >
              Answer
            </h3>
            <CopyButton text={answer} />
          </div>
          <p className="text-base leading-relaxed text-slate-700">{answer}</p>
        </section>
      )}

      <Confidence verdicts={verdicts} ratio={ratio} />

      <Disagreements verdicts={verdicts} />

      {verdicts.length > 0 && (
        <section aria-labelledby="claims-heading" className="flex flex-col gap-2">
          <h3
            id="claims-heading"
            className="font-mono text-xs tracking-widest text-slate-400 uppercase"
          >
            Claims
          </h3>
          <ul className="flex flex-col gap-2" data-testid="claims-list">
            {flaggedFirst(verdicts).map((v) => (
              <ClaimCard key={v.claim} verdict={v} />
            ))}
          </ul>
        </section>
      )}

      <Citations citations={state.citations} />

      {!refused && <SafetyBanner state={state} />}
    </div>
  );
}
