import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { VerificationView } from "@/components/VerificationView";
import { initialStreamState, type ClaimVerdict, type StreamState } from "@/lib/verification";

afterEach(cleanup);

const VERDICTS: ClaimVerdict[] = [
  {
    claim: "Aspirin reduces the risk of a second heart attack.",
    verdict: "Supported",
    quoted_span: "low-dose aspirin lowered recurrent myocardial infarction",
    reasoning: "Directly stated by the cited trial.",
    source_index: 1,
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

  // Confidence: 1 of 3 claims supported → 33%.
  expect(screen.getByText(/1 of 3 claims grounded in evidence/)).toBeDefined();
  expect(screen.getByText("33%")).toBeDefined();
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
  expect(screen.getByText(/1 of 1 claims grounded in evidence/)).toBeDefined();
  expect(screen.getByText("100%")).toBeDefined();
});

it("shows 0% confidence when no claim is grounded (corpus has no relevant evidence)", () => {
  const state = doneState();
  const none: ClaimVerdict[] = [
    { claim: "Smoking causes cancer.", verdict: "Unverifiable", quoted_span: null, reasoning: "Not in evidence." },
    { claim: "Tobacco contains carcinogens.", verdict: "Unverifiable", quoted_span: null, reasoning: "Not in evidence." },
  ];
  state.verdicts = none;
  state.result = { ...state.result!, verdicts: none, has_unsupported_claims: true, support_ratio: 0 };

  render(<VerificationView state={state} />);
  expect(screen.getByText("0%")).toBeDefined();
  expect(screen.getByText(/0 of 2 claims grounded in evidence/)).toBeDefined();
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

it("gives a backend-down hint when the API is unreachable", () => {
  const errored: StreamState = {
    ...initialStreamState,
    status: "error",
    error: "Failed to fetch",
  };
  render(<VerificationView state={errored} />);
  const alert = screen.getByRole("alert");
  expect(alert.textContent).toContain("isn’t reachable");
  expect(alert.textContent).toContain("make dev");
});

it("explains the free-tier wake-up instead of `make dev` on the deployed demo", () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "https://aletheia-demo.example");
  const errored: StreamState = {
    ...initialStreamState,
    status: "error",
    error: "Failed to fetch",
  };
  render(<VerificationView state={errored} />);
  const alert = screen.getByRole("alert");
  expect(alert.textContent).toContain("take up to a minute to wake");
  expect(alert.textContent).not.toContain("make dev");
  vi.unstubAllEnvs();
});

it("orders claims flagged-first, regardless of input order", () => {
  const state = doneState(); // VERDICTS is [Supported, Contradicted, Unverifiable]
  render(<VerificationView state={state} />);

  const badges = screen
    .getByTestId("claims-list")
    .querySelectorAll("li > div > span:last-child");
  const order = Array.from(badges).map((el) => el.textContent);
  expect(order).toEqual(["Contradicted", "Unverifiable", "Supported"]);
});

it("shows a decline notice and no answer when the intake guard refuses a query", () => {
  const refused: StreamState = {
    ...initialStreamState,
    status: "done",
    stages: ["intake", "refusal"],
    result: {
      query: "write py code for a star pattern",
      candidate_answer: "",
      verdicts: [],
      has_unsupported_claims: false,
      support_ratio: 1,
      refused: true,
      refusal_reason: "This question is outside Aletheia's scope.",
    },
  };
  render(<VerificationView state={refused} />);

  const card = screen.getByTestId("refusal");
  expect(within(card).getByText("Request declined")).toBeDefined();
  expect(within(card).getByText(/outside Aletheia's scope/)).toBeDefined();
  // No fabricated answer, no confidence meter, and the advisory banner is suppressed.
  expect(screen.queryByRole("meter")).toBeNull();
  expect(screen.queryByRole("note")).toBeNull();
});

it("labels the source as the user's document when the run used caller-supplied evidence", () => {
  // No retrieval happened: the retriever was skipped and there are no corpus citations.
  const state = doneState();
  state.stages = ["generator", "verifier", "aggregator", "guardrail"];
  state.citations = [];

  render(<VerificationView state={state} userEvidence />);

  const card = screen.getByTestId("user-document-source");
  expect(within(card as HTMLElement).getByText("Your document")).toBeDefined();
  expect(card.textContent).toContain("user-supplied evidence");
  expect(card.textContent).toContain("no trust tier");
});

it("keeps corpus citations authoritative even when the userEvidence flag is set", () => {
  // Defensive: if citations exist, they are what grounded the run — show them.
  render(<VerificationView state={doneState()} userEvidence />);

  expect(screen.queryByTestId("user-document-source")).toBeNull();
  expect(screen.getByRole("link", { name: /Secondary prevention with aspirin/ })).toBeDefined();
});

it("links a resolved quoted span to its citation entry", () => {
  render(<VerificationView state={doneState()} />);

  // The blockquote carries a [n] chip anchoring to the citation the span came from…
  const chip = screen.getByRole("link", { name: "Jump to source 1" });
  expect(chip.getAttribute("href")).toBe("#citation-1");
  expect(chip.textContent).toBe("[1]");
  // …and the citation list item is the anchor target.
  expect(document.getElementById("citation-1")).not.toBeNull();
});

it("renders no source chip for a span the backend could not resolve", () => {
  render(<VerificationView state={doneState()} />);

  // Only the first verdict carries a source_index; the others must not grow a chip.
  expect(screen.getAllByRole("link", { name: /Jump to source/ })).toHaveLength(1);
});
