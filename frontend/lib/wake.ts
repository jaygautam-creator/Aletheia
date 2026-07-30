// Cold-start disclosure for the free-tier backend.
//
// The Render free instance spins down after 15 minutes idle, so the first request from a
// cold visitor waits ~40-60s while the container boots and the embedding model loads. An
// unlabelled spinner reads as "broken"; a labelled, progressing wait reads as "starting".
// The logic here is pure so it is unit-tested without a network or a clock.

/**
 * Rough time for a cold free instance to answer /health. Used only to pace the progress
 * indicator — never to decide whether the backend is actually up (that is the probe's job).
 */
export const COLD_START_ESTIMATE_MS = 55_000;

/** How long a probe may hang before we conclude the instance is asleep, not merely slow. */
export const PROBE_TIMEOUT_MS = 2_500;

/** Gap between retry probes once we know we are waiting on a cold start. */
export const PROBE_INTERVAL_MS = 3_000;

export type WakeStatus =
  /** No probe has resolved yet — say nothing, the backend is usually warm. */
  | "unknown"
  /** The backend answered promptly; there is nothing to disclose. */
  | "awake"
  /** The first probe timed out: a cold start is underway. */
  | "waking"
  /** A cold start finished during this visit. */
  | "ready"
  /** Repeated probes failed for long enough that this is likely not a cold start. */
  | "unreachable";

/**
 * How full to draw the progress bar after `elapsedMs` of waiting.
 *
 * Asymptotic, and capped below 1: the bar must never sit at "100%" while the service is
 * still booting, because a full bar that does not resolve is exactly the broken-spinner
 * feeling this component exists to avoid. Only `status === "ready"` fills it.
 */
export function wakeProgress(elapsedMs: number): number {
  if (elapsedMs <= 0) return 0;
  // Time constant chosen so the bar reads ~80% around the estimate and creeps after.
  const tau = COLD_START_ESTIMATE_MS / 1.7;
  return Math.min(1 - Math.exp(-elapsedMs / tau), 0.95);
}

/**
 * Plain-language status line for the wait. Each stage names what is actually happening,
 * so a visitor who waits 50 seconds knows why and that it is expected.
 */
export function wakeMessage(elapsedMs: number): string {
  if (elapsedMs < 8_000) return "Waking the demo server…";
  if (elapsedMs < 25_000) return "Cold start in progress — the free instance is booting.";
  if (elapsedMs < COLD_START_ESTIMATE_MS) return "Loading the retrieval model — the slow part.";
  return "Taking longer than usual. Still trying…";
}

/** Whole seconds waited, for the counter beside the message. */
export function elapsedSeconds(elapsedMs: number): number {
  return Math.max(0, Math.floor(elapsedMs / 1000));
}

/**
 * Give up on "this is a cold start" after ~3x the estimate. Past that the likelier
 * explanations are a suspended service or a bad API URL, and claiming otherwise would
 * keep a visitor waiting on something that will not arrive.
 */
export function hasGivenUp(elapsedMs: number): boolean {
  return elapsedMs > COLD_START_ESTIMATE_MS * 3;
}
