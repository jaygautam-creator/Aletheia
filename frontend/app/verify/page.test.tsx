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

it("fills the query and runs when an example chip is clicked", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, body: streamOf(FRAMES) }));
  vi.stubGlobal("fetch", fetchMock);

  render(<VerifyPage />);
  fireEvent.click(screen.getByRole("button", { name: /A supported claim/ }));

  const field = screen.getByRole("textbox", { name: /Question or claim/ }) as HTMLTextAreaElement;
  expect(field.value).toContain("ALDH1");
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(await screen.findByText("Supported")).toBeDefined();
});

it("requires a document before verifying in own-document mode, then sends it as evidence", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, body: streamOf(FRAMES) }));
  vi.stubGlobal("fetch", fetchMock);

  render(<VerifyPage />);
  fireEvent.click(screen.getByRole("radio", { name: /My own document/ }));

  // A claim alone is not enough in this mode — the document is the evidence.
  fireEvent.change(screen.getByRole("textbox", { name: /Question or claim/ }), {
    target: { value: "The Eiffel Tower opened in 1889." },
  });
  const button = screen.getByRole("button", { name: /^Verify$/ });
  expect(button.hasAttribute("disabled")).toBe(true);

  fireEvent.change(screen.getByRole("textbox", { name: /Your document/ }), {
    target: { value: "The tower opened to the public on 15 May 1889." },
  });
  expect(button.hasAttribute("disabled")).toBe(false);
  fireEvent.click(button);

  expect(await screen.findByText("Supported")).toBeDefined();
  const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
  expect(body.evidence).toContain("15 May 1889");
  // The provenance card names the user's document as the source.
  expect(screen.getByTestId("user-document-source")).toBeDefined();
});

it("fills both fields and runs when an own-document example chip is clicked", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, body: streamOf(FRAMES) }));
  vi.stubGlobal("fetch", fetchMock);

  render(<VerifyPage />);
  fireEvent.click(screen.getByRole("radio", { name: /My own document/ }));
  fireEvent.click(screen.getByRole("button", { name: /A history claim/ }));

  const doc = screen.getByRole("textbox", { name: /Your document/ }) as HTMLTextAreaElement;
  expect(doc.value).toContain("15 May 1889");
  expect(fetchMock).toHaveBeenCalledOnce();
  const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
  expect(body.query).toContain("Eiffel Tower");
  expect(body.evidence).toContain("World's Fair");
  expect(await screen.findByText("Supported")).toBeDefined();
});

it("shows a Cancel button while streaming and returns to idle when clicked", async () => {
  // A stream that stays open so the run remains in flight.
  const pending = new ReadableStream<Uint8Array>({ start() {} });
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, body: pending })));

  render(<VerifyPage />);
  fireEvent.change(screen.getByRole("textbox", { name: /Question or claim/ }), {
    target: { value: "Does aspirin help the heart?" },
  });
  fireEvent.click(screen.getByRole("button", { name: /^Verify$/ }));

  const cancelButton = await screen.findByRole("button", { name: /Cancel/ });
  fireEvent.click(cancelButton);

  // Back to the pre-run state: the Verify button is shown again.
  expect(screen.getByRole("button", { name: /^Verify$/ })).toBeDefined();
  expect(screen.queryByRole("button", { name: /Cancel/ })).toBeNull();
});
