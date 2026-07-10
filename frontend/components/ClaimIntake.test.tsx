import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ClaimIntake } from "@/components/ClaimIntake";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function stubExtractResponse(payload: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({ ok, status, json: async () => payload });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

it("uploads a chosen PDF and hands the extracted text to onText", async () => {
  stubExtractResponse({ kind: "pdf", text: "Aspirin reduces risk.", characters: 21, truncated: false });
  const onText = vi.fn();
  render(<ClaimIntake onText={onText} />);

  const file = new File(["%PDF"], "claim.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByLabelText("Upload a PDF"), { target: { files: [file] } });

  await waitFor(() => expect(onText).toHaveBeenCalledWith("Aspirin reduces risk."));
});

it("mentions truncation when only the head of a long document came through", async () => {
  stubExtractResponse({ kind: "pdf", text: "long…", characters: 4000, truncated: true });
  render(<ClaimIntake onText={vi.fn()} />);

  const file = new File(["%PDF"], "paper.pdf", { type: "application/pdf" });
  fireEvent.change(screen.getByLabelText("Upload a PDF"), { target: { files: [file] } });

  await waitFor(() => expect(screen.getByText(/only the beginning/i)).toBeTruthy());
});

it("shows the backend's error and recovers", async () => {
  stubExtractResponse({ detail: "No legible text was found in the image." }, false, 422);
  const onText = vi.fn();
  render(<ClaimIntake onText={onText} />);

  const file = new File(["…"], "blur.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText("Upload an image"), { target: { files: [file] } });

  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain("No legible text was found"),
  );
  expect(onText).not.toHaveBeenCalled();
});

it("falls back to an audio file picker when recording is unsupported", () => {
  // jsdom has no MediaRecorder, so the voice chip must open a file input instead.
  render(<ClaimIntake onText={vi.fn()} />);

  expect(screen.getByLabelText("Upload an audio recording")).toBeTruthy();
});

it("disables the intake while a verification is streaming", () => {
  render(<ClaimIntake onText={vi.fn()} disabled />);

  const buttons = screen.getAllByRole("button");
  expect(buttons.length).toBeGreaterThanOrEqual(3);
  for (const button of buttons) {
    expect((button as HTMLButtonElement).disabled).toBe(true);
  }
});
