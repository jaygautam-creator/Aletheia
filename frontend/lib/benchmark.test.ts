import { expect, it } from "vitest";

import {
  baselineSystem,
  benchmark,
  groundedSystem,
  provenanceCaption,
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
