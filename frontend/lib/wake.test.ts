import { describe, expect, it } from "vitest";

import {
  COLD_START_ESTIMATE_MS,
  elapsedSeconds,
  hasGivenUp,
  wakeMessage,
  wakeProgress,
} from "@/lib/wake";

describe("wakeProgress", () => {
  it("starts empty", () => {
    expect(wakeProgress(0)).toBe(0);
    expect(wakeProgress(-500)).toBe(0);
  });

  it("increases monotonically with the wait", () => {
    const samples = [1_000, 5_000, 15_000, 30_000, 55_000].map(wakeProgress);
    for (let i = 1; i < samples.length; i += 1) {
      expect(samples[i]).toBeGreaterThan(samples[i - 1]);
    }
  });

  it("never reaches full, however long the wait", () => {
    // The whole point: a bar pinned at 100% while nothing happens reads as broken.
    expect(wakeProgress(COLD_START_ESTIMATE_MS)).toBeLessThan(1);
    expect(wakeProgress(10 * COLD_START_ESTIMATE_MS)).toBeLessThanOrEqual(0.95);
  });

  it("reads as most of the way there by the time the estimate elapses", () => {
    expect(wakeProgress(COLD_START_ESTIMATE_MS)).toBeGreaterThan(0.75);
  });
});

describe("wakeMessage", () => {
  it("names a distinct stage as the wait lengthens", () => {
    const stages = [0, 12_000, 40_000, 90_000].map(wakeMessage);
    expect(new Set(stages).size).toBe(4);
  });

  it("admits when the wait has exceeded the expected cold start", () => {
    expect(wakeMessage(COLD_START_ESTIMATE_MS + 1)).toMatch(/longer than usual/i);
  });
});

describe("elapsedSeconds", () => {
  it("floors to whole seconds and never goes negative", () => {
    expect(elapsedSeconds(1_999)).toBe(1);
    expect(elapsedSeconds(-1_000)).toBe(0);
  });
});

describe("hasGivenUp", () => {
  it("holds out for a normal cold start", () => {
    expect(hasGivenUp(COLD_START_ESTIMATE_MS)).toBe(false);
  });

  it("stops blaming the cold start well past the estimate", () => {
    expect(hasGivenUp(COLD_START_ESTIMATE_MS * 3 + 1)).toBe(true);
  });
});
