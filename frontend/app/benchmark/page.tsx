import type { Metadata } from "next";
import Link from "next/link";

import { BenchmarkChart } from "@/components/BenchmarkChart";
import { Reveal } from "@/components/Reveal";
import { benchmark, provenanceCaption } from "@/lib/benchmark";

export const metadata: Metadata = {
  title: "Benchmark — Aletheia",
  description:
    "How Aletheia's grounded multi-agent verifier compares to a single-LLM baseline on the SciFact benchmark: catch rate, false agreement, accuracy, latency, and cost.",
};

const GITHUB = "https://github.com/jaygautam-creator/Aletheia";

const COLUMNS = [
  { key: "accuracy", label: "Accuracy", suffix: "%", better: "high" },
  { key: "catch_rate", label: "Catch rate", suffix: "%", better: "high" },
  { key: "false_agreement", label: "False agreement", suffix: "%", better: "low" },
  { key: "latency_p50", label: "Latency p50", suffix: "s", better: "low" },
  { key: "tokens_per_query", label: "Tokens/query", suffix: "", better: "low" },
] as const;

const METHOD = [
  {
    title: "Three arms, one variable",
    body: "The single-LLM baseline, an ungrounded multi-agent arm, and the grounded verifier judge the same claims against the same retrieved evidence with the same model. Only the verification architecture changes, so every gap is architectural.",
  },
  {
    title: "Seeded and reproducible",
    body: "Claims are drawn with a fixed seed and each configuration is repeated; rates are reported as mean ± standard deviation. A single command re-runs the suite and rewrites these numbers in place.",
  },
  {
    title: "Paired significance",
    body: "Because every system judges the same claims, the gaps are tested on the paired per-claim predictions — an exact McNemar test on accuracy and bootstrap confidence intervals on the catch-rate and false-agreement deltas.",
  },
] as const;

function isGrounded(name: string): boolean {
  return /aletheia|grounded/i.test(name);
}

export default function BenchmarkPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-16 px-6 pt-20 pb-28">
      <header className="flex flex-col gap-4">
        <p className="animate-fade-up font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
          the evaluation harness
        </p>
        <h1
          className="animate-fade-up max-w-3xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-slate-900 sm:text-6xl"
          style={{ animationDelay: "0.08s" }}
        >
          The centerpiece is the{" "}
          <span className="shimmer-text italic">measurement</span>.
        </h1>
        <p
          className="animate-fade-up max-w-2xl text-lg leading-relaxed text-slate-600"
          style={{ animationDelay: "0.16s" }}
        >
          Every feature exists to be measured here. The system is run repeatedly over a public
          benchmark and scored against a single-LLM baseline — so the headline is a table, not a
          claim.
        </p>
      </header>

      <Reveal>
        <BenchmarkChart />
      </Reveal>

      {/* Full results table */}
      <Reveal className="flex flex-col gap-4">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-slate-900">
          Full results
        </h2>
        <div className="glass overflow-x-auto rounded-2xl">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-900/10 text-left">
                <th className="px-4 py-3 font-medium text-slate-500">System</th>
                {COLUMNS.map((col) => (
                  <th key={col.key} className="px-4 py-3 text-right font-medium text-slate-500">
                    {col.label}
                    <span className="ml-1 font-mono text-[10px] text-slate-400">
                      {col.better === "high" ? "↑" : "↓"}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.systems.map((system) => (
                <tr
                  key={system.name}
                  className={
                    isGrounded(system.name)
                      ? "border-b border-slate-900/5 bg-teal-50/40 last:border-0"
                      : "border-b border-slate-900/5 last:border-0"
                  }
                >
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {system.name}
                    {isGrounded(system.name) && (
                      <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.5 font-mono text-[10px] tracking-wide text-teal-700 uppercase">
                        ours
                      </span>
                    )}
                  </td>
                  {COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className="px-4 py-3 text-right text-slate-700 tabular-nums"
                    >
                      {system[col.key].toFixed(1)}
                      {col.suffix}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="font-mono text-xs text-slate-400">{provenanceCaption()}</p>
      </Reveal>

      {/* Methodology */}
      <Reveal className="flex flex-col gap-6">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-slate-900">
          How it&rsquo;s measured
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {METHOD.map((m) => (
            <div key={m.title} className="glass flex flex-col gap-2 rounded-2xl p-5">
              <h3 className="font-serif text-lg font-medium text-slate-900">{m.title}</h3>
              <p className="text-sm leading-relaxed text-slate-600">{m.body}</p>
            </div>
          ))}
        </div>
        <p className="text-sm leading-relaxed text-slate-500">
          The current numbers are free-tier-bounded (small sample, single seed); the machinery
          for the full seeded sweep with the ablation arm and significance testing is in place.
          Full methodology and the generated tables live in{" "}
          <a
            href={`${GITHUB}/blob/main/EVALUATION.md`}
            target="_blank"
            rel="noreferrer"
            className="text-teal-700 underline-offset-2 hover:underline"
          >
            EVALUATION.md
          </a>
          .
        </p>
      </Reveal>

      <div className="flex flex-wrap gap-4">
        <Link
          href="/verify"
          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-teal-600 to-cyan-500 px-6 py-3 text-sm font-medium text-white shadow-[0_10px_30px_-8px_rgba(13,148,136,0.6)] transition hover:brightness-105"
        >
          Try the live verification →
        </Link>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/60 px-6 py-3 text-sm text-slate-600 transition hover:border-teal-300 hover:text-teal-700"
        >
          ← Back to overview
        </Link>
      </div>
    </main>
  );
}
