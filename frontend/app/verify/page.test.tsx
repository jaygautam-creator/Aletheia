import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import VerifyPage from "@/app/verify/page";

afterEach(() => {
  cleanup();
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
  'event: generator\ndata: {"candidate_answer":"Aspirin has cardiovascular benefits.",'
    + '"claims":["Aspirin reduces heart-attack risk."]}\n\n',
  'event: verifier\ndata: {"verdicts":[{"claim":"Aspirin reduces heart-attack risk.",'
    + '"verdict":"Supported","quoted_span":"aspirin lowered recurrent infarction","reasoning":"r"}]}\n\n',
  "event: done\ndata: {}\n\n",
];

it("disables the submit button until a question is entered", () => {
  render(<VerifyPage />);
  const button = screen.getByRole("button", { name: /Verify/ });
  expect(button.hasAttribute("disabled")).toBe(true);

  fireEvent.change(screen.getByRole("textbox", { name: /Question or claim/ }), {
    target: { value: "Does aspirin help the heart?" },
  });
  expect(button.hasAttribute("disabled")).toBe(false);
});

it("submits the query and renders the streamed verdict", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, status: 200, body: streamOf(FRAMES) })),
  );

  render(<VerifyPage />);
  fireEvent.change(screen.getByRole("textbox", { name: /Question or claim/ }), {
    target: { value: "Does aspirin help the heart?" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Verify/ }));

  // The streamed verifier event lands and the verdict card renders.
  expect(await screen.findByText("Supported")).toBeDefined();
  expect(screen.getByText(/aspirin lowered recurrent infarction/)).toBeDefined();
  expect(screen.getByText("Aspirin has cardiovascular benefits.")).toBeDefined();
});
