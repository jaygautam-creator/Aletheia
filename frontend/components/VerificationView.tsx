// Presentational view for the streamed verification path.
//
// It renders a `StreamState` (produced by useVerificationStream) and is intentionally
// pure — no hooks, no network — so it can be unit-tested with crafted states. The route
// at app/verify wires the hook's live state into this component.

import type { Advisory, Citation, ClaimVerdict, StreamState, Verdict } from "@/lib/verification";

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

const STAGE_DOT: Record<StageState, string> = {
  done: "bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.5)]",
  active: "bg-sky-400 animate-pulse shadow-[0_0_10px_2px_rgba(56,189,248,0.6)]",
  skipped: "bg-neutral-700",
  pending: "bg-neutral-800",
};

const VERDICT_STYLE: Record<Verdict, string> = {
  Supported: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  Contradicted: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  Unverifiable: "border-amber-500/30 bg-amber-500/10 text-amber-300",
};

const ADVISORY_STYLE: Record<Advisory, string> = {
  info: "border-sky-500/30 bg-sky-500/10 text-sky-100",
  caution: "border-amber-500/30 bg-amber-500/10 text-amber-100",
  high_caution: "border-rose-500/30 bg-rose-500/10 text-rose-100",
};

const ADVISORY_LABEL: Record<Advisory, string> = {
  info: "Advisory",
  caution: "Caution",
  high_caution: "High caution",
};

function PipelineProgress({ state }: { state: StreamState }) {
  const streaming = state.status === "streaming";
  return (
    <ol aria-label="Verification pipeline" className="flex flex-col gap-1.5">
      {CANONICAL_STAGES.map((stage) => {
        const status = stageState(stage.id, state.stages, streaming);
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
                  ? "text-neutral-600"
                  : "font-medium text-neutral-100"
              }
            >
              {stage.label}
            </span>
            <span className="text-xs text-neutral-500">{stage.detail}</span>
            {status === "skipped" && (
              <span className="font-mono text-[10px] tracking-wide text-neutral-600 uppercase">
                skipped
              </span>
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
      className={`flex flex-col gap-2 rounded-xl border px-4 py-3 text-sm ${ADVISORY_STYLE[safety.advisory]}`}
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
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs tracking-widest text-neutral-500 uppercase">
          Confidence
        </span>
        <span className="text-sm text-neutral-400">
          <span className="font-semibold text-neutral-50">{pct}%</span>
          {" — "}
          {supported} of {verdicts.length} claims grounded in evidence
        </span>
      </div>
      <div
        role="meter"
        aria-label="Share of claims supported by evidence"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06]"
      >
        <div
          className="h-full rounded-full bg-emerald-400 shadow-[0_0_12px_1px_rgba(52,211,153,0.6)]"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ClaimCard({ verdict }: { verdict: ClaimVerdict }) {
  return (
    <li className="flex flex-col gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-neutral-100">{verdict.claim}</p>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${VERDICT_STYLE[verdict.verdict]}`}
        >
          {verdict.verdict}
        </span>
      </div>
      {verdict.quoted_span && (
        <blockquote className="border-l-2 border-emerald-400/40 pl-3 text-sm text-neutral-300 italic">
          “{verdict.quoted_span}”
        </blockquote>
      )}
      {verdict.reasoning && <p className="text-xs text-neutral-500">{verdict.reasoning}</p>}
    </li>
  );
}

function Disagreements({ verdicts }: { verdicts: ClaimVerdict[] }) {
  const flagged = verdicts.filter((v) => v.verdict !== "Supported");
  if (flagged.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-rose-500/30 bg-rose-500/[0.08] px-4 py-3">
      <p className="text-sm font-medium text-rose-200">
        {flagged.length} {flagged.length === 1 ? "claim is" : "claims are"} not supported by the
        evidence
      </p>
      <ul className="flex flex-col gap-1 text-sm text-rose-300/90">
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
        className="font-mono text-xs tracking-widest text-neutral-500 uppercase"
      >
        Sources
      </h3>
      <ol className="flex flex-col gap-1.5">
        {citations.map((c) => (
          <li key={c.index} className="flex gap-2 text-sm">
            <span className="font-mono text-neutral-600">[{c.index}]</span>
            <span className="flex flex-col">
              {c.url ? (
                <a
                  href={c.url}
                  className="text-neutral-200 underline-offset-4 transition-colors hover:text-emerald-300 hover:underline"
                  rel="noreferrer"
                  target="_blank"
                >
                  {c.title}
                </a>
              ) : (
                <span className="text-neutral-200">{c.title}</span>
              )}
              <span className="font-mono text-xs text-neutral-600">
                {c.connector} · {c.trust_tier} · {c.score.toFixed(2)}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function VerificationView({ state }: { state: StreamState }) {
  if (state.status === "idle") {
    return (
      <p className="text-sm text-neutral-500" data-testid="idle-hint">
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

  return (
    <div className="flex flex-col gap-6">
      <div
        role="status"
        aria-live="polite"
        aria-busy={state.status === "streaming"}
        className="flex flex-col gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5"
      >
        <span className="font-mono text-xs tracking-widest text-neutral-500 uppercase">
          {state.status === "streaming" ? "Verifying…" : "Pipeline"}
        </span>
        <PipelineProgress state={state} />
      </div>

      {state.status === "error" && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
        >
          {state.error ?? "Something went wrong."}
        </div>
      )}

      <SafetyBanner state={state} />

      {answer && (
        <section aria-labelledby="answer-heading" className="flex flex-col gap-2">
          <h3
            id="answer-heading"
            className="font-mono text-xs tracking-widest text-neutral-500 uppercase"
          >
            Answer
          </h3>
          <p className="text-base leading-relaxed text-neutral-200">{answer}</p>
        </section>
      )}

      <Confidence verdicts={verdicts} ratio={ratio} />

      <Disagreements verdicts={verdicts} />

      {verdicts.length > 0 && (
        <section aria-labelledby="claims-heading" className="flex flex-col gap-2">
          <h3
            id="claims-heading"
            className="font-mono text-xs tracking-widest text-neutral-500 uppercase"
          >
            Claims
          </h3>
          <ul className="flex flex-col gap-2">
            {verdicts.map((v) => (
              <ClaimCard key={v.claim} verdict={v} />
            ))}
          </ul>
        </section>
      )}

      <Citations citations={state.citations} />
    </div>
  );
}
