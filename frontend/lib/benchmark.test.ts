import { expect, it } from "vitest";

import {
  baselineSystem,
  benchmark,
  groundedSystem,
  provenanceCaption,
  ungroundedSystem,
  type BenchmarkResults,
} from "@/lib/benchmark";

it("exposes a well-formed benchmark record", () => {
  expect(benchmark.systems.length).toBeGreaterThanOrEqual(2);
  expect(benchmark.n).toBeGreaterThan(0);
  expect(benchmark.model).toBeTruthy();
});

it("resolves the baseline and grounded systems by name", () => {
  expect(baselineSystem()?.name).toMatch(/baseline/i);
  expect(groundedSystem()?.name).toMatch(/aletheia|grounded/i);
});

it("shows the grounded verifier catching more than the baseline", () => {
  // A guard on the numbers the whole site leans on: the headline direction must hold.
  expect(groundedSystem()!.catch_rate).toBeGreaterThan(baselineSystem()!.catch_rate);
  expect(groundedSystem()!.false_agreement).toBeLessThan(baselineSystem()!.false_agreement);
});

it("builds a provenance caption carrying the dataset, n, and model", () => {
  const caption = provenanceCaption();
  expect(caption).toContain(benchmark.dataset);
  expect(caption).toContain(`n = ${benchmark.n}`);
  expect(caption).toContain(benchmark.model);
});

it("does not let the ungrounded ablation row shadow the real grounded row", () => {
  // Regression test: "ungrounded" contains "grounded" as a substring, so a naive
  // /grounded/i match returns the ablation row instead — .find() takes the first
  // match, and the ablation row comes before the Aletheia row in every real run.
  // Both rows can even satisfy a directional assertion against baseline, which is
  // exactly how this slipped through before: the numbers looked plausible either way.
  const fixture: BenchmarkResults = {
    dataset: "SciFact dev",
    n: 100,
    seed: 7,
    repeats: 1,
    model: "groq:llama-3.1-8b-instant",
    date: "2026-07-19",
    systems: [
      { name: "Single-LLM baseline", accuracy: 60, catch_rate: 60.3, false_agreement: 37.7, latency_p50: 0.3, tokens_per_query: 1388 },
      { name: "Multi-agent, ungrounded (ablation)", accuracy: 65, catch_rate: 65.5, false_agreement: 35.7, latency_p50: 14.06, tokens_per_query: 1473.2 },
      { name: "Aletheia (grounded verifier)", accuracy: 69, catch_rate: 82.8, false_agreement: 23.8, latency_p50: 0.41, tokens_per_query: 1675.6 },
    ],
  };

  expect(groundedSystem(fixture)?.name).toBe("Aletheia (grounded verifier)");
  expect(groundedSystem(fixture)?.catch_rate).toBe(82.8);
  expect(ungroundedSystem(fixture)?.name).toBe("Multi-agent, ungrounded (ablation)");
});
