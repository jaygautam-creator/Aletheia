"use client";

import { useInView } from "@/lib/motion";

// A live visualization of the five-agent pipeline: a claim enters at the Retriever and
// arrives grounded at the Guardrail. The connector flows continuously and each stage
// node pulses in sequence, so the figure reads as a running system rather than a static
// diagram. Rendered as an accessible ordered list; the motion is decorative.

const STAGES = [
  { name: "Retriever", detail: "hybrid evidence search" },
  { name: "Generator", detail: "answer + atomic claims" },
  { name: "Verifier", detail: "verdict + quoted span" },
  { name: "Aggregator", detail: "support + disagreements" },
  { name: "Guardrail", detail: "advisory + disclaimer" },
] as const;

export function PipelineFlow() {
  const { ref, inView } = useInView<HTMLDivElement>();

  return (
    <div ref={ref} className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
            The verification pipeline
          </span>
          <p className="max-w-xl text-sm leading-relaxed text-slate-500">
            A claim enters at the Retriever and arrives grounded at the Guardrail — each stage
            inspectable, timed, and traced.
          </p>
        </div>
        <span className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-teal-500" />
          live path
        </span>
      </div>

      <ol
        aria-label="Verification pipeline"
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
      >
        {STAGES.map((stage, index) => (
          <li
            key={stage.name}
            className="glass glow-hover group relative flex flex-col gap-2 rounded-2xl p-4"
          >
            {/* Flowing connector into the next stage (desktop only) */}
            {index < STAGES.length - 1 && (
              <svg
                aria-hidden
                className="absolute top-8 -right-3 hidden h-4 w-6 lg:block"
                viewBox="0 0 24 16"
              >
                <line
                  x1="0"
                  y1="8"
                  x2="24"
                  y2="8"
                  stroke="url(#flowGrad)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  className={inView ? "flow-line" : ""}
                />
                <defs>
                  <linearGradient id="flowGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#0d9488" />
                    <stop offset="100%" stopColor="#22d3ee" />
                  </linearGradient>
                </defs>
              </svg>
            )}
            <span className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-2.5 w-2.5 rounded-full bg-gradient-to-r from-teal-600 to-cyan-400 shadow-[0_0_10px_1px_rgba(13,148,136,0.6)]"
                style={
                  inView
                    ? { animation: `node-pulse 2.2s ease-in-out ${index * 0.32}s infinite` }
                    : undefined
                }
              />
              <span className="font-mono text-[10px] text-slate-400">
                {String(index + 1).padStart(2, "0")}
              </span>
            </span>
            <span className="text-sm font-medium text-slate-900">{stage.name}</span>
            <span className="text-xs leading-relaxed text-slate-500">{stage.detail}</span>
          </li>
        ))}
      </ol>

      <p className="text-xs leading-relaxed text-slate-400">
        The Retriever runs only when you don&rsquo;t supply evidence; the Guardrail runs last and
        is advisory — it never edits a verdict.
      </p>
    </div>
  );
}
