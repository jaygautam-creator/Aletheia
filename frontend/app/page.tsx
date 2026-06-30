import Link from "next/link";

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
    body: "Unsupported claims are called out explicitly instead of being smoothed over into a confident answer.",
  },
  {
    title: "Measured, not claimed",
    body: "A seeded evaluation harness reports catch rate, false-agreement, latency, and cost against a single-LLM baseline.",
  },
] as const;

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-20 px-6 pt-20 pb-24">
      <header className="flex flex-col gap-5">
        <p className="font-mono text-xs tracking-[0.25em] text-emerald-400/90 uppercase">
          ἀλήθεια · unconcealment
        </p>
        <h1 className="bg-gradient-to-br from-white via-white to-neutral-500 bg-clip-text text-5xl font-semibold tracking-tight text-transparent sm:text-7xl">
          Truth, unconcealed.
        </h1>
        <p className="max-w-2xl text-lg leading-relaxed text-neutral-400">
          Aletheia is an evidence-grounded, multi-agent verification framework — with a rigorous
          evaluation harness — that improves the reliability of LLM answers by grounding every claim
          in real evidence and surfacing disagreement instead of hiding it.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-5">
          <Link
            href="/verify"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-medium text-neutral-950 shadow-[0_0_28px_-6px_rgba(16,185,129,0.7)] transition hover:bg-emerald-400 hover:shadow-[0_0_36px_-4px_rgba(16,185,129,0.9)]"
          >
            Try the live verification →
          </Link>
          <a
            className="font-mono text-xs text-neutral-500 underline-offset-4 transition-colors hover:text-neutral-300 hover:underline"
            href="https://github.com/jaygautam-creator/Aletheia"
            target="_blank"
            rel="noreferrer"
          >
            View source ↗
          </a>
        </div>
      </header>

      <section aria-labelledby="pipeline-heading" className="flex flex-col gap-5">
        <h2
          id="pipeline-heading"
          className="font-mono text-xs tracking-[0.25em] text-neutral-500 uppercase"
        >
          The verification pipeline
        </h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {PIPELINE.map((stage, index) => (
            <li
              key={stage.name}
              className="group flex flex-col gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 transition-colors hover:border-emerald-400/30 hover:bg-white/[0.04]"
            >
              <span className="flex items-center gap-2">
                <span
                  aria-hidden
                  className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.55)]"
                />
                <span className="font-mono text-[10px] text-neutral-600">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </span>
              <span className="text-sm font-medium text-neutral-100">{stage.name}</span>
              <span className="text-xs leading-relaxed text-neutral-500">{stage.detail}</span>
            </li>
          ))}
        </ol>
        <p className="text-xs leading-relaxed text-neutral-600">
          The Retriever runs only when you don&rsquo;t supply evidence; the Guardrail runs last and
          is advisory — it never edits a verdict.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        {PRINCIPLES.map((p) => (
          <div
            key={p.title}
            className="flex flex-col gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] p-5"
          >
            <h3 className="text-sm font-medium text-neutral-100">{p.title}</h3>
            <p className="text-sm leading-relaxed text-neutral-500">{p.body}</p>
          </div>
        ))}
      </section>

      <footer className="font-mono text-xs text-neutral-600">MIT © 2026 Jay Gautam</footer>
    </main>
  );
}
