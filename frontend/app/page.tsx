import Link from "next/link";

import { BenchmarkChart } from "@/components/BenchmarkChart";

const PIPELINE = [
  { name: "Retriever", detail: "hybrid evidence search" },
  { name: "Generator", detail: "answer + atomic claims" },
  { name: "Verifier", detail: "verdict + quoted span" },
  { name: "Aggregator", detail: "answer · confidence · disagreements" },
  { name: "Guardrail", detail: "advisory + disclaimer" },
] as const;

const PRINCIPLES = [
  {
    title: "Grounded, not guessed",
    body: "Every verdict must quote the exact source span that justifies it — or it is flagged as unsupported.",
  },
  {
    title: "Disagreement, surfaced",
    body: "Unsupported claims are called out explicitly instead of being smoothed into a confident-sounding answer.",
  },
  {
    title: "Measured, not claimed",
    body: "A seeded evaluation harness reports catch rate, false agreement, latency, and cost against a single-LLM baseline.",
  },
] as const;


export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-24 px-6 pt-20 pb-28">
      <section className="flex flex-col gap-6">
        <p className="animate-fade-up font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
          ἀλήθεια · evidence-grounded verification
        </p>
        <h1
          className="animate-fade-up max-w-3xl font-serif text-5xl leading-[1.05] font-medium tracking-tight text-slate-900 sm:text-7xl"
          style={{ animationDelay: "0.08s" }}
        >
          Medical answers you can{" "}
          <span className="bg-gradient-to-r from-teal-600 to-cyan-500 bg-clip-text text-transparent italic">
            verify
          </span>
          , not just trust.
        </h1>
        <p
          className="animate-fade-up max-w-2xl text-lg leading-relaxed text-slate-600"
          style={{ animationDelay: "0.16s" }}
        >
          Aletheia is a multi-agent framework that grounds every claim in the medical literature —
          quoting the exact evidence that supports it, and surfacing what isn&rsquo;t supported
          instead of hiding it behind a confident tone.
        </p>
        <div
          className="animate-fade-up mt-2 flex flex-wrap items-center gap-5"
          style={{ animationDelay: "0.24s" }}
        >
          <Link
            href="/verify"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-teal-600 to-cyan-500 px-6 py-3 text-sm font-medium text-white shadow-[0_10px_30px_-8px_rgba(13,148,136,0.6)] transition hover:shadow-[0_14px_38px_-8px_rgba(13,148,136,0.8)] hover:brightness-105"
          >
            Try the live verification →
          </Link>
          <a
            className="text-sm text-slate-500 underline-offset-4 transition-colors hover:text-slate-900 hover:underline"
            href="https://github.com/jaygautam-creator/Aletheia"
            target="_blank"
            rel="noreferrer"
          >
            View source ↗
          </a>
        </div>
      </section>

      <BenchmarkChart />

      <section aria-labelledby="pipeline-heading" className="flex flex-col gap-6">
        <h2
          id="pipeline-heading"
          className="font-mono text-xs tracking-[0.25em] text-slate-400 uppercase"
        >
          The verification pipeline
        </h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {PIPELINE.map((stage, index) => (
            <li
              key={stage.name}
              className="animate-fade-up flex flex-col gap-2 rounded-2xl border border-white/60 bg-white/60 p-4 shadow-[0_12px_40px_-28px_rgba(12,27,42,0.4)] backdrop-blur-md transition hover:-translate-y-0.5 hover:shadow-[0_18px_48px_-26px_rgba(13,148,136,0.5)]"
              style={{ animationDelay: `${index * 0.08}s` }}
            >
              <span className="flex items-center gap-2">
                <span
                  aria-hidden
                  className="h-2 w-2 rounded-full bg-gradient-to-r from-teal-600 to-cyan-400 shadow-[0_0_8px_1px_rgba(13,148,136,0.5)]"
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
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        {PRINCIPLES.map((p) => (
          <div
            key={p.title}
            className="flex flex-col gap-2 rounded-2xl border border-white/60 bg-white/60 p-6 shadow-[0_12px_40px_-28px_rgba(12,27,42,0.4)] backdrop-blur-md"
          >
            <h3 className="font-serif text-lg font-medium text-slate-900">{p.title}</h3>
            <p className="text-sm leading-relaxed text-slate-600">{p.body}</p>
          </div>
        ))}
      </section>

      <footer className="font-mono text-xs text-slate-400">MIT © 2026 Jay Gautam</footer>
    </main>
  );
}
