import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useVerificationStream } from "@/lib/useVerificationStream";

afterEach(() => {
  vi.restoreAllMocks();
});

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

const FRAMES = [
  'event: retriever\ndata: {"citations":[{"index":1,"title":"Aspirin","connector":"pubmed",'
    + '"external_id":"40000001","url":null,"trust_tier":"curated_corpus","score":0.4}]}\n\n',
  'event: verifier\ndata: {"verdicts":[{"claim":"c","verdict":"Supported",'
    + '"quoted_span":"x","reasoning":"r"}]}\n\n',
  'event: guardrail\ndata: {"safety":{"advisory":"info",'
    + '"disclaimer":"does not provide medical advice","notes":[]}}\n\n',
  "event: done\ndata: {}\n\n",
];

it("accumulates streamed stages into the final state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, status: 200, body: streamOf(FRAMES) })),
  );

  const { result } = renderHook(() => useVerificationStream());
  await act(async () => {
    await result.current.start({ query: "Does aspirin help the heart?" });
  });

  const state = result.current.state;
  expect(state.status).toBe("done");
  expect(state.stages).toEqual(["retriever", "verifier", "guardrail"]);
  expect(state.citations[0].external_id).toBe("40000001");
  expect(state.verdicts[0].verdict).toBe("Supported");
  expect(state.safety?.advisory).toBe("info");
});

it("surfaces a non-ok response as an error", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503, body: null })));

  const { result } = renderHook(() => useVerificationStream());
  await act(async () => {
    await result.current.start({ query: "q" });
  });

  expect(result.current.state.status).toBe("error");
  expect(result.current.state.error).toContain("503");
});

it("surfaces a fetch failure (backend unreachable) as an error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }),
  );

  const { result } = renderHook(() => useVerificationStream());
  await act(async () => {
    await result.current.start({ query: "q" });
  });

  expect(result.current.state.status).toBe("error");
  expect(result.current.state.error).toContain("Failed to fetch");
});

it("cancel returns the state to idle and does not report an abort as an error", async () => {
  // A stream that never closes, so the run stays in flight until cancelled.
  const pending = new ReadableStream<Uint8Array>({ start() {} });
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, body: pending })));

  const { result } = renderHook(() => useVerificationStream());
  act(() => {
    void result.current.start({ query: "q" });
  });
  await act(async () => {
    result.current.cancel();
  });

  expect(result.current.state.status).toBe("idle");
  expect(result.current.state.error).toBeNull();
});
