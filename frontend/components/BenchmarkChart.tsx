"use client";

import type { CSSProperties } from "react";

import {
  baselineSystem,
  benchmark,
  groundedSystem,
  provenanceCaption,
} from "@/lib/benchmark";
import { useCountUp, useInView } from "@/lib/motion";

// Reads its numbers from the single generated source of truth (lib/benchmark.ts), so the
// chart can never drift from EVALUATION.md. Bars grow and their labels count up when the
// figure scrolls into view.

const baseline = baselineSystem();
const grounded = groundedSystem();

const METRICS = [
  {
    name: "Hallucination catch",
    baseline: baseline?.catch_rate ?? 0,
    aletheia: grounded?.catch_rate ?? 0,
    higherBetter: true,
  },
  {
    name: "Verification accuracy",
    baseline: baseline?.accuracy ?? 0,
    aletheia: grounded?.accuracy ?? 0,
    higherBetter: true,
  },
  {
    name: "False agreement",
    baseline: baseline?.false_agreement ?? 0,
    aletheia: grounded?.false_agreement ?? 0,
    higherBetter: false,
  },
] as const;

function Bar({
  value,
  variant,
  animate,
}: {
  value: number;
  variant: "baseline" | "aletheia";
  animate: boolean;
}) {
  const shown = useCountUp(value, animate);
  const fill =
    variant === "aletheia"
      ? "bg-gradient-to-t from-teal-600 to-cyan-400 shadow-[0_0_24px_-6px_rgba(13,148,136,0.7)]"
      : "bg-slate-300";
  return (
    <div className="flex h-full w-9 items-end sm:w-11">
      <div
        className={`relative w-full rounded-t-lg ${fill} transition-[height] duration-1000 ease-out`}
        style={{ height: animate ? `${value}%` : 0 } as CSSProperties}
      >
        <span
          className={`absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-semibold tabular-nums text-slate-700 transition-opacity duration-500 ${animate ? "opacity-100" : "opacity-0"}`}
        >
          {shown.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

export function BenchmarkChart() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <figure ref={ref} className="glass flex flex-col gap-6 rounded-3xl p-7">
      <figcaption className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-xs tracking-[0.2em] text-teal-700 uppercase">
            Measured, not claimed
          </span>
          <h2 className="font-serif text-2xl font-medium tracking-tight text-slate-900">
            Aletheia vs. a single-LLM baseline
          </h2>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-slate-300" /> Baseline
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-gradient-to-t from-teal-600 to-cyan-400" />
            Aletheia
          </span>
        </div>
      </figcaption>

      <div className="grid grid-cols-3 gap-3 sm:gap-6">
        {METRICS.map((m) => (
          <div key={m.name} className="flex flex-col items-center gap-3">
            <div className="flex h-44 w-full items-end justify-center gap-2 border-b border-slate-900/10 sm:gap-3">
              <Bar value={m.baseline} variant="baseline" animate={inView} />
              <Bar value={m.aletheia} variant="aletheia" animate={inView} />
            </div>
            <div className="flex flex-col items-center gap-0.5 text-center">
              <span className="text-xs font-medium text-slate-700">{m.name}</span>
              {!m.higherBetter && (
                <span className="text-[10px] text-slate-400">↓ lower is better</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs leading-relaxed text-slate-400">
        {provenanceCaption()}. Same model for both systems. Full methodology in{" "}
        <a
          href="https://github.com/jaygautam-creator/Aletheia/blob/main/EVALUATION.md"
          target="_blank"
          rel="noreferrer"
          className="underline-offset-2 hover:text-teal-600 hover:underline"
        >
          EVALUATION.md §6.2
        </a>
        . {benchmark.n < 50 ? "Free-tier-bounded; scaling up is next." : ""}
      </p>
    </figure>
  );
}
