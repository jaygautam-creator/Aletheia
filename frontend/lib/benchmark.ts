// The benchmark numbers the UI renders, imported from a single generated source of
// truth (frontend/lib/benchmark-results.json), which `make phase3-bench --write-frontend`
// rewrites. Keeping this typed here means the landing chart and the /benchmark page can
// never drift from each other or from EVALUATION.md.

import results from "@/lib/benchmark-results.json";

export interface BenchmarkSystem {
  name: string;
  accuracy: number;
  catch_rate: number;
  false_agreement: number;
  latency_p50: number;
  tokens_per_query: number;
}

export interface BenchmarkResults {
  dataset: string;
  n: number;
  seed: number;
  repeats: number;
  model: string;
  date: string;
  systems: BenchmarkSystem[];
}

export const benchmark: BenchmarkResults = results as BenchmarkResults;

/** The single-LLM baseline row (the comparator every metric is reported against). */
export function baselineSystem(data: BenchmarkResults = benchmark): BenchmarkSystem | undefined {
  return data.systems.find((s) => /baseline/i.test(s.name));
}

/** The grounded Aletheia row (the headline system).
 *
 * Uses word boundaries so "grounded" does not also match "ungrounded" — without them,
 * `.find()` returns the ablation row instead (it comes first in `systems`), silently
 * showing the wrong numbers on the landing page and `/benchmark`.
 */
export function groundedSystem(data: BenchmarkResults = benchmark): BenchmarkSystem | undefined {
  return data.systems.find((s) => /\baletheia\b|\bgrounded\b/i.test(s.name));
}

/** The ungrounded ablation row, present only when a run included the H2 arm. */
export function ungroundedSystem(data: BenchmarkResults = benchmark): BenchmarkSystem | undefined {
  return data.systems.find((s) => /ungrounded|ablation/i.test(s.name));
}

/** A one-line provenance caption shared by the chart and the benchmark page. */
export function provenanceCaption(data: BenchmarkResults = benchmark): string {
  const runs = data.repeats === 1 ? "single seed" : `${data.repeats} seeded runs`;
  return `${data.dataset} · n = ${data.n}, ${runs} · ${data.model} · ${data.date}`;
}
