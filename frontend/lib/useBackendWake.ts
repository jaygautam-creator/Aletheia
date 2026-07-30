"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  hasGivenUp,
  PROBE_INTERVAL_MS,
  PROBE_TIMEOUT_MS,
  type WakeStatus,
} from "@/lib/wake";

const HEALTH_URL = `${process.env.NEXT_PUBLIC_API_URL ?? ""}/health`;

/**
 * Probe /health once with a short deadline.
 *
 * No `credentials: "include"` — this is a plain public GET, so it stays a CORS-simple
 * request and cannot be blocked by a credentials/origin mismatch while the real API is
 * still booting. Resolves false on timeout, network error, or non-2xx.
 */
async function probe(signal: AbortSignal): Promise<boolean> {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), PROBE_TIMEOUT_MS);
  const onOuterAbort = () => timeout.abort();
  signal.addEventListener("abort", onOuterAbort);
  try {
    const response = await fetch(HEALTH_URL, {
      method: "GET",
      cache: "no-store",
      signal: timeout.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", onOuterAbort);
  }
}

/**
 * Track whether the free-tier backend is awake, and how long a cold start has been running.
 *
 * Probes /health on mount. A prompt answer means the instance is warm and the UI shows
 * nothing. A timeout means a cold start, and the hook keeps probing — reporting elapsed
 * time so the caller can disclose the wait instead of hanging on a bare spinner.
 */
export function useBackendWake(): {
  status: WakeStatus;
  elapsedMs: number;
  retry: () => void;
} {
  const [status, setStatus] = useState<WakeStatus>("unknown");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const startedAt = useRef<number | null>(null);

  const retry = useCallback(() => {
    startedAt.current = null;
    setElapsedMs(0);
    setStatus("unknown");
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let ticker: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;

    async function poll() {
      while (!cancelled) {
        const ok = await probe(controller.signal);
        if (cancelled) return;
        if (ok) {
          // "ready" only if we had actually announced a wait — a warm first probe is
          // "awake" and must render nothing at all.
          setStatus(startedAt.current === null ? "awake" : "ready");
          return;
        }
        if (startedAt.current === null) {
          // First failure: the instance is asleep. Start the clock and the disclosure.
          startedAt.current = Date.now();
          setStatus("waking");
          ticker = setInterval(() => {
            const began = startedAt.current;
            if (began === null) return;
            setElapsedMs(Date.now() - began);
          }, 500);
        } else if (hasGivenUp(Date.now() - startedAt.current)) {
          setStatus("unreachable");
          return;
        }
        await new Promise<void>((resolve) => {
          timer = setTimeout(resolve, PROBE_INTERVAL_MS);
        });
      }
    }

    void poll();

    return () => {
      cancelled = true;
      controller.abort();
      if (timer) clearTimeout(timer);
      if (ticker) clearInterval(ticker);
    };
  }, [attempt]);

  return { status, elapsedMs, retry };
}
