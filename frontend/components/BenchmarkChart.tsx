"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

const METRICS = [
  { name: "Hallucination catch", baseline: 58.3, aletheia: 91.7, higherBetter: true },
  { name: "Verification accuracy", baseline: 65.0, aletheia: 75.0, higherBetter: true },
  { name: "False agreement", baseline: 41.7, aletheia: 16.7, higherBetter: false },
] as const;

function Bar({
  value,
  delay,
  variant,
  animate,
}: {
  value: number;
  delay: number;
  variant: "baseline" | "aletheia";
  animate: boolean;
}) {
  const fill =
    variant === "aletheia"
      ? "bg-gradient-to-t from-teal-600 to-cyan-400 shadow-[0_0_24px_-6px_rgba(13,148,136,0.6)]"
      : "bg-slate-300";
  return (
    <div className="flex h-full w-9 items-end sm:w-11">
      <div
        className={`${animate ? "bar-rise" : ""} relative w-full rounded-t-lg ${fill}`}
        style={
          {
            ["--h"]: `${value}%`,
            ...(animate ? { animationDelay: `${delay}s` } : { height: 0 }),
          } as unknown as CSSProperties
        }
      >
        <span
          className={`absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-semibold tabular-nums text-slate-700 transition-opacity duration-300 ${animate ? "opacity-100" : "opacity-0"}`}
        >
          {value.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

export function BenchmarkChart() {
  const [animate, setAnimate] = useState(false);
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) {
      setAnimate(true);
      return;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setAnimate(true);
          obs.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <figure
      ref={ref}
      className="flex flex-col gap-6 rounded-3xl border border-white/60 bg-white/70 p-7 shadow-[0_24px_70px_-36px_rgba(12,27,42,0.35)] backdrop-blur-xl"
    >
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
        {METRICS.map((m, gi) => (
          <div key={m.name} className="flex flex-col items-center gap-3">
            <div className="flex h-44 w-full items-end justify-center gap-2 border-b border-slate-900/10 sm:gap-3">
              <Bar value={m.baseline} delay={gi * 0.12} variant="baseline" animate={animate} />
              <Bar value={m.aletheia} delay={gi * 0.12 + 0.08} variant="aletheia" animate={animate} />
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
        First live run on the SciFact <code className="font-mono">dev</code> split (n = 20, single
        seed), same model for both systems. Full methodology in EVALUATION.md §6.2.
      </p>
    </figure>
  );
}
