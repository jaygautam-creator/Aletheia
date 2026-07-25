import { fever, feverBaseline, feverGrounded, feverUngrounded } from "@/lib/fever";

// The FEVER second-domain block for /benchmark. SciFact (above it on the page) is the
// headline where grounding wins outright; this section is the honest robustness story on a
// deliberately harder, open-domain benchmark: the anti-hallucination guarantee holds, catch
// and false-agreement still beat the baseline, and the raw-accuracy trade-off is stated
// plainly rather than hidden. Numbers come from lib/fever.ts; analysis in EVALUATION.md §6.6.

const EVAL_66 =
  "https://github.com/jaygautam-creator/Aletheia/blob/main/EVALUATION.md#66-second-domain--fever-open-domain-wikipedia-claims";

const g = feverGrounded;
const b = feverBaseline;
const u = feverUngrounded;

// Two honest wins vs the single-LLM baseline (lower false-agreement is better), plus the
// raw-accuracy trade-off carried as its own, differently-styled tile.
const WINS = [
  {
    label: "Hallucinations caught",
    value: g?.catch_rate ?? 0,
    compare: b?.catch_rate ?? 0,
    better: "high" as const,
  },
  {
    label: "False-agreement rate",
    value: g?.false_agreement ?? 0,
    compare: b?.false_agreement ?? 0,
    better: "low" as const,
  },
];

function WinTile({
  label,
  value,
  compare,
  better,
}: {
  label: string;
  value: number;
  compare: number;
  better: "high" | "low";
}) {
  const wins = better === "high" ? value > compare : value < compare;
  return (
    <div className="glass flex flex-col gap-1 rounded-2xl p-5">
      <span className="font-serif text-3xl font-medium text-slate-900 tabular-nums">
        {value.toFixed(1)}%
      </span>
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <span className="font-mono text-[11px] text-slate-400">
        {wins ? "beats" : "vs"} {compare.toFixed(1)}% single-LLM
      </span>
    </div>
  );
}

export function FeverSecondDomain() {
  const guaranteeHolds =
    fever.guarantee.asserted > 0 &&
    fever.guarantee.verbatim_backed === fever.guarantee.asserted;

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <span className="font-mono text-xs tracking-[0.2em] text-teal-700 uppercase">
          second domain · stress test
        </span>
        <h2 className="font-serif text-2xl font-medium tracking-tight text-slate-900">
          Does the guarantee hold when the domain is against it?
        </h2>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">
          SciFact (above) is the headline. FEVER is a harder, open-domain benchmark whose claims
          are crowdworker <em>paraphrases</em> of Wikipedia — exactly the case where a true
          claim&rsquo;s wording does not match its evidence, so a verbatim-grounding system is
          tested where it is weakest. Same 8B model, {fever.n} claims, seed {fever.seed}.
        </p>
      </div>

      {/* The load-bearing result: the anti-hallucination guarantee held. */}
      <div className="glass flex flex-col gap-2 rounded-2xl border border-teal-500/20 bg-teal-50/40 p-6">
        <div className="flex items-baseline gap-3">
          <span className="font-serif text-4xl font-medium text-teal-700 tabular-nums">
            {fever.guarantee.verbatim_backed}/{fever.guarantee.asserted}
          </span>
          <span className="text-sm font-medium text-slate-700">
            asserted verdicts backed by an exact verbatim quote
          </span>
        </div>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">
          {guaranteeHolds ? "The guarantee held: every" : "Of the"} Supported/Contradicted verdict
          quotes a span that appears verbatim in the retrieved evidence — no unsupported
          assertion, even in the adversarial domain. The guarantee is <em>never assert without a
          quote</em>; it is not a promise of perfect reasoning, and this section reports both
          sides of that honestly.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {WINS.map((w) => (
          <WinTile key={w.label} {...w} />
        ))}
        {/* The raw-accuracy trade-off, carried plainly rather than dropped. */}
        <div className="glass flex flex-col gap-1 rounded-2xl border border-amber-400/30 p-5">
          <span className="font-serif text-3xl font-medium text-slate-900 tabular-nums">
            {g?.accuracy.toFixed(1)}%
          </span>
          <span className="text-sm font-medium text-slate-700">Verification accuracy</span>
          <span className="font-mono text-[11px] text-slate-400">
            trades ~{((u?.accuracy ?? 0) - (g?.accuracy ?? 0)).toFixed(0)} pp vs {u?.accuracy.toFixed(1)}% free-reasoning
          </span>
        </div>
      </div>

      <p className="max-w-3xl text-sm leading-relaxed text-slate-500">
        The honest trade-off: strict verbatim grounding costs raw accuracy on paraphrase claims
        (77.0% grounded vs 85.0% for the same model reasoning freely), while it still catches more
        hallucinations and endorses fewer false claims than the single-LLM baseline. Cleaning the
        corpus markup lifted grounded accuracy from 56.0% to 77.0% on these same claims. Full
        analysis, confusion matrix, and significance in{" "}
        <a
          href={EVAL_66}
          target="_blank"
          rel="noreferrer"
          className="text-teal-700 underline-offset-2 hover:underline"
        >
          EVALUATION.md §6.6
        </a>
        .
      </p>
    </section>
  );
}
