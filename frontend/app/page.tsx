import Link from "next/link";

import { BenchmarkChart } from "@/components/BenchmarkChart";
import { ExampleVerdict } from "@/components/ExampleVerdict";
import { HeroAperture } from "@/components/HeroAperture";
import { HeroStats } from "@/components/HeroStats";
import { PipelineFlow } from "@/components/PipelineFlow";
import { Reveal } from "@/components/Reveal";

const STEPS = [
  {
    n: "01",
    title: "Bring evidence, in three ways",
    body: "Ask a medical question and a hybrid semantic + keyword search pulls the most relevant passages from a frozen corpus of biomedical abstracts. Bring your own document and check a claim from any field against it. Or ask something general with no document — a live, clearly lower-trust Wikipedia lookup fills in instead of refusing.",
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
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-28 px-6 pt-16 pb-28 sm:pt-20">
      {/* Hero */}
      <section className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="flex flex-col gap-6">
          <p className="animate-fade-up font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
            ἀλήθεια · evidence-grounded verification
          </p>
          <h1
            className="animate-fade-up max-w-3xl font-serif text-5xl leading-[1.03] font-medium tracking-tight text-slate-900 sm:text-7xl"
            style={{ animationDelay: "0.08s" }}
          >
            Answers you can{" "}
            <span className="shimmer-text italic">verify</span>, not just trust.
          </h1>
          <p
            className="animate-fade-up max-w-2xl text-lg leading-relaxed text-slate-600"
            style={{ animationDelay: "0.16s" }}
          >
            Aletheia is a multi-agent framework that grounds every claim in evidence — the
            curated medical literature by default, your own document for any topic, or a live
            Wikipedia lookup for a general question — quoting the exact text that supports it,
            and surfacing what isn&rsquo;t supported instead of hiding it behind a confident tone.
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
            <Link
              href="/benchmark"
              className="text-sm text-slate-500 underline-offset-4 transition-colors hover:text-slate-900 hover:underline"
            >
              See the benchmark →
            </Link>
          </div>
        </div>

        <div
          className="animate-fade-up mx-auto hidden lg:block"
          style={{ animationDelay: "0.2s" }}
        >
          <HeroAperture />
        </div>
      </section>

      <div className="animate-fade-up" style={{ animationDelay: "0.32s" }}>
        <HeroStats />
      </div>

      <Reveal>
        <ExampleVerdict />
      </Reveal>

      <Reveal id="benchmark" className="scroll-mt-24 flex flex-col gap-3">
        <BenchmarkChart />
        <Link
          href="/benchmark"
          className="self-start text-sm text-teal-700 underline-offset-4 hover:underline"
        >
          Full results, all three systems, and methodology →
        </Link>
      </Reveal>

      {/* How it works — plain language before jargon */}
      <section aria-labelledby="how-heading" className="flex flex-col gap-8">
        <Reveal className="flex flex-col gap-2">
          <span className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
            How it works
          </span>
          <h2
            id="how-heading"
            className="max-w-2xl font-serif text-2xl font-medium tracking-tight text-slate-900 sm:text-3xl"
          >
            Three steps between a claim and a verdict you can check.
          </h2>
        </Reveal>
        <ol className="grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal as="li" key={step.n} delay={i * 90} className="flex flex-col gap-3">
              <span className="font-mono text-sm text-teal-600">{step.n}</span>
              <span className="h-px w-full bg-gradient-to-r from-teal-300/70 to-transparent" />
              <h3 className="font-serif text-lg font-medium text-slate-900">{step.title}</h3>
              <p className="text-sm leading-relaxed text-slate-600">{step.body}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      {/* Animated pipeline — the technical detail under the plain-language story */}
      <Reveal>
        <PipelineFlow />
      </Reveal>

      {/* Principles */}
      <section className="grid gap-3 sm:grid-cols-3">
        {PRINCIPLES.map((p, i) => (
          <Reveal
            key={p.title}
            delay={i * 90}
            className="glass glow-hover flex flex-col gap-2 rounded-2xl p-6"
          >
            <h3 className="font-serif text-lg font-medium text-slate-900">{p.title}</h3>
            <p className="text-sm leading-relaxed text-slate-600">{p.body}</p>
          </Reveal>
        ))}
      </section>

      {/* Safety boundary — always visible, per ADR-0002 */}
      <Reveal className="rounded-2xl border border-teal-200/70 bg-teal-50/40 px-6 py-5 backdrop-blur-md">
        <p className="text-sm leading-relaxed text-slate-600">
          <span className="font-medium text-slate-900">Research tool — not medical advice.</span>{" "}
          Aletheia verifies whether a claim is supported by the medical literature; it does not
          diagnose, treat, or give medical advice. Always consult a qualified healthcare
          professional.
        </p>
      </Reveal>

      <footer className="flex flex-col gap-3 border-t border-slate-900/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-xs text-slate-400">MIT © 2026 Jay Gautam</span>
        <nav className="flex flex-wrap items-center gap-5 text-xs text-slate-500">
          <Link href="/benchmark" className="hover:text-slate-900">
            Benchmark
          </Link>
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
