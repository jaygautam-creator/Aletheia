// A static, real specimen of the pipeline's output for the landing page.
//
// The data below is an ACTUAL grounded verdict from a Phase 3 benchmark run over the
// SciFact `dev` split (corpus of 5,183 abstracts), copied verbatim from the recorded
// trace in backend/runs/scifact_dev.jsonl — not a mock-up. The two claims share the
// *same* evidence sentence and take opposite stances; the system judges each correctly,
// which is the whole point: grounding reads the direction of the evidence, it does not
// pattern-match the topic. Keep this in sync if the corpus/run changes.

type SpecimenVerdict = "Supported" | "Contradicted" | "Unverifiable";

interface Specimen {
  claim: string;
  verdict: SpecimenVerdict;
  quotedSpan: string;
  note: string;
}

const EVIDENCE_TITLE = "ALDH1 expression and prognosis in breast carcinoma";

const SPECIMENS: readonly Specimen[] = [
  {
    claim: "ALDH1 expression is associated with better breast cancer outcomes.",
    verdict: "Contradicted",
    quotedSpan:
      "In a series of 577 breast carcinomas, expression of ALDH1 detected by immunostaining correlated with poor prognosis.",
    note: "A plausible-sounding claim — the evidence says the opposite direction, and it is flagged.",
  },
  {
    claim: "ALDH1 expression is associated with poorer prognosis in breast cancer.",
    verdict: "Supported",
    quotedSpan:
      "In a series of 577 breast carcinomas, expression of ALDH1 detected by immunostaining correlated with poor prognosis.",
    note: "The same evidence supports the correctly-directed claim — affirmed, with the span quoted.",
  },
];

const VERDICT_STYLE: Record<SpecimenVerdict, string> = {
  Supported: "border-teal-300 bg-teal-50 text-teal-800",
  Contradicted: "border-rose-300 bg-rose-50 text-rose-700",
  Unverifiable: "border-amber-300 bg-amber-50 text-amber-800",
};

function SpecimenCard({ specimen }: { specimen: Specimen }) {
  return (
    <li className="flex flex-col gap-3 rounded-2xl border border-white/70 bg-white/80 p-5 shadow-[0_16px_50px_-34px_rgba(12,27,42,0.45)] backdrop-blur-md">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm leading-relaxed font-medium text-slate-900">{specimen.claim}</p>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${VERDICT_STYLE[specimen.verdict]}`}
        >
          {specimen.verdict}
        </span>
      </div>
      <blockquote className="border-l-2 border-teal-400 pl-3 text-sm leading-relaxed text-slate-600 italic">
        &ldquo;{specimen.quotedSpan}&rdquo;
      </blockquote>
      <p className="text-xs leading-relaxed text-slate-500">{specimen.note}</p>
    </li>
  );
}

/** The landing-page "see it work" specimen — a real grounded verdict pair. */
export function ExampleVerdict() {
  return (
    <section aria-labelledby="specimen-heading" className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <span className="font-mono text-xs tracking-[0.25em] text-teal-700 uppercase">
          See it work
        </span>
        <h2
          id="specimen-heading"
          className="max-w-2xl font-serif text-2xl font-medium tracking-tight text-slate-900 sm:text-3xl"
        >
          A verdict is only valid if it can quote the evidence.
        </h2>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
          Two claims, the same source sentence, opposite directions. The system affirms one
          and flags the other — because a <span className="text-slate-900">Supported</span> or{" "}
          <span className="text-slate-900">Contradicted</span> verdict must point at the exact
          span that justifies it, or it is downgraded to Unverifiable.
        </p>
      </div>

      <ul className="grid gap-3 sm:grid-cols-2">
        {SPECIMENS.map((specimen) => (
          <SpecimenCard key={specimen.claim} specimen={specimen} />
        ))}
      </ul>

      <p className="font-mono text-xs leading-relaxed text-slate-400">
        Actual output · source: {EVIDENCE_TITLE} · SciFact <code>dev</code> · corpus of 5,183
        abstracts.
      </p>
    </section>
  );
}
