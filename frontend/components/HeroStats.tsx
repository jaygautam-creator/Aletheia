"use client";

import { baselineSystem, groundedSystem } from "@/lib/benchmark";
import { useCountUp, useInView } from "@/lib/motion";

// The headline result, up front, with the numbers counting up on entry. Reads the two
// rates from the generated benchmark record (single source of truth); the corpus size is
// a fixed property of the ingested SciFact corpus.

const CORPUS_ABSTRACTS = 5183;

const grounded = groundedSystem();
const baseline = baselineSystem();

const STATS = [
  {
    value: grounded?.catch_rate ?? 0,
    decimals: 1,
    suffix: "%",
    label: "hallucinations caught",
    sub: `vs ${(baseline?.catch_rate ?? 0).toFixed(1)}% single-LLM`,
  },
  {
    value: grounded?.false_agreement ?? 0,
    decimals: 1,
    suffix: "%",
    label: "false-agreement rate",
    sub: `vs ${(baseline?.false_agreement ?? 0).toFixed(1)}% single-LLM`,
  },
  {
    value: CORPUS_ABSTRACTS,
    decimals: 0,
    suffix: "",
    label: "abstracts grounded on",
    sub: "frozen SciFact corpus",
  },
] as const;

function Stat({
  value,
  decimals,
  suffix,
  label,
  sub,
  active,
}: {
  value: number;
  decimals: number;
  suffix: string;
  label: string;
  sub: string;
  active: boolean;
}) {
  const shown = useCountUp(value, active);
  const formatted =
    decimals === 0
      ? Math.round(shown).toLocaleString()
      : shown.toFixed(decimals);
  return (
    <a
      href="/benchmark"
      className="glass glow-hover flex flex-col gap-0.5 rounded-2xl p-4"
    >
      <span className="font-serif text-3xl font-medium text-slate-900 tabular-nums">
        {formatted}
        {suffix}
      </span>
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <span className="font-mono text-[11px] text-slate-400">{sub}</span>
    </a>
  );
}

export function HeroStats() {
  const { ref, inView } = useInView<HTMLDivElement>();
  return (
    <div ref={ref} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {STATS.map((stat) => (
        <Stat key={stat.label} {...stat} active={inView} />
      ))}
    </div>
  );
}
