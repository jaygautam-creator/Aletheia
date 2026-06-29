import { describe, expect, it } from "vitest";

import {
  applyEvent,
  initialStreamState,
  parseSSE,
  type StreamEvent,
} from "@/lib/verification";

describe("parseSSE", () => {
  it("extracts complete frames and keeps a trailing partial as rest", () => {
    const { events, rest } = parseSSE(
      'event: generator\ndata: {"claims":["c"]}\n\nevent: verifier\ndata: {"verdic',
    );

    expect(events).toHaveLength(1);
    expect(events[0].event).toBe("generator");
    expect(events[0].data.claims).toEqual(["c"]);
    expect(rest).toBe('event: verifier\ndata: {"verdic'); // incomplete, carried over
  });

  it("tolerates malformed JSON by yielding an empty payload", () => {
    const { events } = parseSSE("event: oops\ndata: {not json}\n\n");

    expect(events[0].event).toBe("oops");
    expect(events[0].data).toEqual({});
  });

  it("parses the done event with an empty object", () => {
    const { events } = parseSSE("event: done\ndata: {}\n\n");
    expect(events[0]).toEqual({ event: "done", data: {} });
  });
});

describe("applyEvent", () => {
  it("folds stage payloads into accumulating state", () => {
    let state = initialStreamState;
    const events: StreamEvent[] = [
      { event: "retriever", data: { citations: [citation()] } },
      { event: "generator", data: { candidate_answer: "ans", claims: ["c"] } },
      { event: "verifier", data: { verdicts: [verdict()] } },
      { event: "guardrail", data: { safety: safety() } },
      { event: "done", data: {} },
    ];

    for (const event of events) state = applyEvent(state, event);

    expect(state.status).toBe("done");
    expect(state.stages).toEqual(["retriever", "generator", "verifier", "guardrail"]);
    expect(state.citations[0].external_id).toBe("40000001");
    expect(state.candidateAnswer).toBe("ans");
    expect(state.verdicts[0].verdict).toBe("Supported");
    expect(state.safety?.advisory).toBe("info");
  });

  it("marks the stream errored and records the detail", () => {
    const state = applyEvent(initialStreamState, {
      event: "error",
      data: { detail: "model exploded" },
    });

    expect(state.status).toBe("error");
    expect(state.error).toBe("model exploded");
  });
});

function citation() {
  return {
    index: 1,
    title: "Aspirin trial",
    connector: "pubmed",
    external_id: "40000001",
    url: null,
    trust_tier: "curated_corpus",
    score: 0.42,
  };
}

function verdict() {
  return {
    claim: "Aspirin reduces cardiovascular risk.",
    verdict: "Supported" as const,
    quoted_span: "aspirin reduces cardiovascular risk",
    reasoning: "stated",
  };
}

function safety() {
  return { advisory: "info" as const, disclaimer: "does not provide medical advice", notes: [] };
}
