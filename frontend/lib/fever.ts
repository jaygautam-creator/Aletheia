// FEVER second-domain numbers, kept in a SEPARATE record from the SciFact headline
// (frontend/lib/benchmark-results.json) on purpose: FEVER is a harder, open-domain
// stress test that does NOT beat the baseline on accuracy, so it must never flow through
// the SciFact `--write-frontend` path and overwrite the flagship. It is shown as an
// explicitly-labelled second domain on /benchmark. Full analysis: EVALUATION.md §6.6.

import results from "@/lib/fever-results.json";

export interface FeverSystem {
  name: string;
  accuracy: number;
  catch_rate: number;
  false_agreement: number;
}

export interface FeverResults {
  dataset: string;
  n: number;
  seed: number;
  model: string;
  date: string;
  coverage: number;
  /** The anti-hallucination guarantee, measured directly on this run's traces. */
  guarantee: { asserted: number; verbatim_backed: number };
  systems: FeverSystem[];
}

export const fever: FeverResults = results as FeverResults;

function find(pattern: RegExp): FeverSystem | undefined {
  return fever.systems.find((s) => pattern.test(s.name));
}

/** The single-LLM baseline row (the comparator the honest wins are stated against). */
export const feverBaseline = find(/baseline/i);

/** The grounded Aletheia row. Word boundaries keep "grounded" from matching "ungrounded". */
export const feverGrounded = find(/\baletheia\b|\bgrounded\b/i);

/** The ungrounded ablation — the free-reasoning ceiling the grounded arm trades accuracy against. */
export const feverUngrounded = find(/ungrounded|ablation/i);
