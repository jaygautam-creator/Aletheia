import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { VerificationView } from "@/components/VerificationView";
import { initialStreamState, type ClaimVerdict, type StreamState } from "@/lib/verification";

afterEach(cleanup);

const VERDICTS: ClaimVerdict[] = [
  {
    claim: "Aspirin reduces the risk of a second heart attack.",
    verdict: "Supported",
    quoted_span: "low-dose aspirin lowered recurrent myocardial infarction",
    reasoning: "Directly stated by the cited trial.",
  },
  {
    claim: "Aspirin cures the common cold.",
    verdict: "Contradicted",
    quoted_span: "no effect on viral upper respiratory infection",
    reasoning: "The source reports no such effect.",
  },
  {
    claim: "Aspirin is the most prescribed drug worldwide.",
    verdict: "Unverifiable",
    quoted_span: null,
    reasoning: "Not addressed by the retrieved evidence.",
  },
];

function doneState(): StreamState {
  return {
    ...initialStreamState,
    status: "done",
    stages: ["retriever", "generator", "verifier", "aggregator", "guardrail"],
    citations: [
      {
        index: 1,
        title: "Secondary prevention with aspirin",
        connector: "pubmed",
        external_id: "40000001",
        url: "https://example.org/40000001",
        trust_tier: "curated_corpus",
        score: 0.82,
      },
    ],
    candidateAnswer: "Aspirin has cardiovascular benefits.",
    verdicts: VERDICTS,
    result: {
      query: "Tell me about aspirin.",
      candidate_answer: "Aspirin has cardiovascular benefits.",
      verdicts: VERDICTS,
      has_unsupported_claims: true,
      support_ratio: 1 / 3,
    },
    safety: {
      advisory: "caution",
      disclaimer: "Aletheia does not provide medical advice.",
      notes: ["Unsupported claims were detected."],
    },
  };
}

it("shows an idle hint before a run starts", () => {
  render(<VerificationView state={initialStreamState} />);
  expect(screen.getByTestId("idle-hint")).toBeDefined();
});

it("marks the latest streamed stage active and a passed-over retriever as skipped", () => {
  const streaming: StreamState = {
    ...initialStreamState,
    status: "streaming",
    stages: ["generator", "verifier"],
    candidateAnswer: "draft answer",
  };
  render(<VerificationView state={streaming} />);

  expect(screen.getByTestId("stage-retriever").getAttribute("data-state")).toBe("skipped");
  expect(screen.getByTestId("stage-generator").getAttribute("data-state")).toBe("done");
  expect(screen.getByTestId("stage-verifier").getAttribute("data-state")).toBe("active");
  expect(screen.getByTestId("stage-aggregator").getAttribute("data-state")).toBe("pending");
  // The partial answer from the generator renders before the run completes.
  expect(screen.getByText("draft answer")).toBeDefined();
});

it("renders verdicts, quoted spans, confidence, and citations on completion", () => {
  render(<VerificationView state={doneState()} />);

  // One card per claim, each with a verdict badge and its reasoning.
  expect(screen.getByText("Supported")).toBeDefined();
  expect(screen.getByText("The source reports no such effect.")).toBeDefined();
  // The supporting quote is shown verbatim.
  expect(screen.getByText(/lowered recurrent myocardial infarction/)).toBeDefined();

  // Confidence: 1 of 3 claims supported.
  expect(screen.getByText("1 of 3 claims grounded in evidence")).toBeDefined();
  const meter = screen.getByRole("meter");
  expect(meter.getAttribute("aria-valuenow")).toBe("33");

  // Sources list.
  expect(screen.getByRole("link", { name: /Secondary prevention with aspirin/ })).toBeDefined();
});

it("surfaces unsupported claims as an explicit disagreement callout", () => {
  render(<VerificationView state={doneState()} />);
  const callout = screen.getByText(/2 claims are not supported by the evidence/);
  const region = callout.closest("div");
  expect(region).not.toBeNull();
  expect(within(region as HTMLElement).getByText(/Aspirin cures the common cold/)).toBeDefined();
  expect(within(region as HTMLElement).getByText(/most prescribed drug worldwide/)).toBeDefined();
});

it("shows the safety advisory with its standing disclaimer", () => {
  render(<VerificationView state={doneState()} />);
  const note = screen.getByRole("note");
  expect(within(note).getByText("Caution")).toBeDefined();
  expect(within(note).getByText(/does not provide medical advice/)).toBeDefined();
});

it("omits the disagreement callout when every claim is supported", () => {
  const allSupported = doneState();
  const supported: ClaimVerdict[] = [
    {
      claim: "Aspirin reduces the risk of a second heart attack.",
      verdict: "Supported",
      quoted_span: "lowered recurrent myocardial infarction",
      reasoning: "Stated by the trial.",
    },
  ];
  allSupported.verdicts = supported;
  allSupported.result = { ...allSupported.result!, verdicts: supported, has_unsupported_claims: false, support_ratio: 1 };

  render(<VerificationView state={allSupported} />);
  expect(screen.queryByText(/not supported by the evidence/)).toBeNull();
  expect(screen.getByText("1 of 1 claims grounded in evidence")).toBeDefined();
});

it("labels a high-caution advisory", () => {
  const state = doneState();
  state.safety = {
    advisory: "high_caution",
    disclaimer: "Aletheia does not provide medical advice.",
    notes: [],
  };
  render(<VerificationView state={state} />);
  expect(screen.getByText("High caution")).toBeDefined();
});

it("renders an error alert when the stream fails", () => {
  const errored: StreamState = {
    ...initialStreamState,
    status: "error",
    error: "request failed (HTTP 503)",
  };
  render(<VerificationView state={errored} />);
  expect(screen.getByRole("alert").textContent).toContain("503");
});
