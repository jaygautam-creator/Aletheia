const PIPELINE = [
  { name: "Guardrail", detail: "screens prompt injection" },
  { name: "Generator", detail: "answer + atomic claims" },
  { name: "Retriever", detail: "hybrid evidence search" },
  { name: "Verifier", detail: "verdict + quoted span" },
  { name: "Aggregator", detail: "answer · confidence · disagreements" },
] as const;

export default function Home() {
  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-12 px-6 py-20">
      <header className="flex flex-col gap-4">
        <p className="font-mono text-sm tracking-widest text-neutral-500 uppercase">
          ἀλήθεια · unconcealment
        </p>
        <h1 className="text-5xl font-semibold tracking-tight sm:text-6xl">Aletheia</h1>
        <p className="max-w-2xl text-lg leading-relaxed text-neutral-600 dark:text-neutral-300">
          An evidence-grounded, multi-agent verification framework — with a rigorous evaluation
          harness — that improves the reliability of LLM answers by grounding every claim in real
          evidence and surfacing disagreement instead of hiding it.
        </p>
      </header>

      <section aria-labelledby="pipeline-heading" className="flex flex-col gap-4">
        <h2
          id="pipeline-heading"
          className="font-mono text-xs tracking-widest text-neutral-500 uppercase"
        >
          The verification pipeline
        </h2>
        <ol className="flex flex-wrap items-stretch gap-2">
          {PIPELINE.map((stage, index) => (
            <li key={stage.name} className="flex items-stretch gap-2">
              <div className="flex flex-col gap-1 rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
                <span className="text-sm font-medium">{stage.name}</span>
                <span className="text-xs text-neutral-500">{stage.detail}</span>
              </div>
              {index < PIPELINE.length - 1 && (
                <span aria-hidden className="self-center text-neutral-400">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-3 rounded-lg border border-dashed border-neutral-300 px-5 py-4 text-sm text-neutral-600 dark:border-neutral-700 dark:text-neutral-300">
        <p>
          <span className="font-medium text-neutral-900 dark:text-neutral-100">
            Phase 0 — Foundation.
          </span>{" "}
          This dashboard is a skeleton. The live agent path, confidence scores, and benchmark
          results land in later phases.
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs text-neutral-500">
          <a
            className="underline-offset-4 hover:underline"
            href="https://github.com/jaygautam-creator/Aletheia"
          >
            github.com/jaygautam-creator/Aletheia
          </a>
          <span>backend → :8000/health</span>
        </div>
      </section>

      <footer className="font-mono text-xs text-neutral-400">MIT © 2026 Jay Gautam</footer>
    </main>
  );
}
