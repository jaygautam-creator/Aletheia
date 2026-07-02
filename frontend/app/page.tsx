import Link from "next/link";

import { BenchmarkChart } from "@/components/BenchmarkChart";
import { ExampleVerdict } from "@/components/ExampleVerdict";

const HEADLINE_STATS = [
  { value: "91.7%", label: "hallucinations caught", sub: "vs 58.3% single-LLM" },
  { value: "16.7%", label: "false-agreement rate", sub: "vs 41.7% single-LLM" },
  { value: "5,183", label: "abstracts grounded on", sub: "frozen SciFact corpus" },
] as const;

const STEPS = [
  {
    n: "01",
    title: "Retrieve real literature",
    body: "A hybrid semantic + keyword search pulls the most relevant passages from a frozen corpus of biomedical abstracts — the only evidence the system is allowed to use.",
  },
  {
    n: "02",
    title: "Break the answer into atomic claims",
    body: "The answer is decomposed into single, independently checkable statements, so each factual assertion is judged on its own instead of hidden inside a fluent paragraph.",
  },
  {
    n: "03",
    title: "Every verdict must quote a span",
    body: "A claim is marked Supported or Contradicted only when the Verifier can quote the exact source text that justifies it — otherwise it is flagged Unverifiable. No quote, no verdict.",
  },
] as const;

const PIPELINE = [
  { name: "Retriever", detail: "hybrid evidence search" },
  { name: "Generator", detail: "answer + atomic claims" },
  { name: "Verifier", detail: "verdict + quoted span" },
  { name: "Aggregator", detail: "answer · support · disagreements" },
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

const GITHUB = "https://github.com/jaygautam-creator/Aletheia";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-28 px-6 pt-20 pb-28">
      {/* Hero */}
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
            href={GITHUB}
            target="_blank"
            rel="noreferrer"
          >
            View source ↗
          </a>
        </div>

        {/* Headline stats — the measured result, up front */}
        <dl
          className="animate-fade-up mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3"
          style={{ animationDelay: "0.32s" }}
        >
          {HEADLINE_STATS.map((stat) => (
            <a
              key={stat.label}
              href="#benchmark"
              className="group flex flex-col gap-0.5 rounded-2xl border border-white/60 bg-white/50 p-4 backdrop-blur-md transition hover:border-teal-200 hover:bg-white/70"
            >
              <dt className="sr-only">{stat.label}</dt>
              <dd className="flex items-baseline gap-2">
                <span className="font-serif text-3xl font-medium text-slate-900 tabular-nums">
                  {stat.value}
                </span>
              </dd>
              <span className="text-sm font-medium text-slate-700">{stat.label}</span>
              <span className="font-mono text-[11px] text-slate-400">{stat.sub}</span>
            </a>
          ))}
        </dl>
      </section>

      <ExampleVerdict />

      <section id="benchmark" className="scroll-mt-24">
        <BenchmarkChart />
      </section>

      {/* How it works — plain language before jargon */}
      <section aria-labelledby="how-heading" className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <span className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
            How it works
          </span>
          <h2
            id="how-heading"
            className="max-w-2xl font-serif text-2xl font-medium tracking-tight text-slate-900 sm:text-3xl"
          >
            Three steps between a claim and a verdict you can check.
          </h2>
        </div>
        <ol className="grid gap-6 sm:grid-cols-3">
          {STEPS.map((step) => (
            <li key={step.n} className="flex flex-col gap-3">
              <span className="font-mono text-sm text-teal-600">{step.n}</span>
              <span className="h-px w-full bg-gradient-to-r from-teal-300/70 to-transparent" />
              <h3 className="font-serif text-lg font-medium text-slate-900">{step.title}</h3>
              <p className="text-sm leading-relaxed text-slate-600">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Pipeline — the technical detail under the plain-language story */}
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
              className="flex flex-col gap-2 rounded-2xl border border-white/60 bg-white/60 p-4 shadow-[0_12px_40px_-28px_rgba(12,27,42,0.4)] backdrop-blur-md transition hover:-translate-y-0.5 hover:shadow-[0_18px_48px_-26px_rgba(13,148,136,0.5)]"
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

      {/* Principles */}
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

      {/* Safety boundary — always visible, per ADR-0002 */}
      <section className="rounded-2xl border border-teal-200/70 bg-teal-50/40 px-6 py-5 backdrop-blur-md">
        <p className="text-sm leading-relaxed text-slate-600">
          <span className="font-medium text-slate-900">Research tool — not medical advice.</span>{" "}
          Aletheia verifies whether a claim is supported by the medical literature; it does not
          diagnose, treat, or give medical advice. Always consult a qualified healthcare
          professional.
        </p>
      </section>

      <footer className="flex flex-col gap-3 border-t border-slate-900/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-xs text-slate-400">MIT © 2026 Jay Gautam</span>
        <nav className="flex flex-wrap items-center gap-5 text-xs text-slate-500">
          <a href={GITHUB} target="_blank" rel="noreferrer" className="hover:text-slate-900">
            GitHub ↗
          </a>
          <a
            href={`${GITHUB}/blob/main/EVALUATION.md`}
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900"
          >
            Evaluation
          </a>
          <a
            href={`${GITHUB}/blob/main/ARCHITECTURE.md`}
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900"
          >
            Architecture
          </a>
        </nav>
      </footer>
    </main>
  );
}
