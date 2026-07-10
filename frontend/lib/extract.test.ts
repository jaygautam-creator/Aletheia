import { afterEach, describe, expect, it, vi } from "vitest";

import { describeExtractFailure, extractFile } from "@/lib/extract";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("extractFile", () => {
  it("posts the file as multipart form data and returns the extraction", async () => {
    const payload = { kind: "pdf", text: "Aspirin reduces risk.", characters: 21, truncated: false };
    const fetchMock = stubFetch({ ok: true, json: async () => payload });

    const result = await extractFile(new Blob(["%PDF"], { type: "application/pdf" }), "claim.pdf");

    expect(result).toEqual(payload);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.get("file")).toBeInstanceOf(File);
    expect((body.get("file") as File).name).toBe("claim.pdf");
  });

  it("surfaces the backend's detail message on a handled failure", async () => {
    stubFetch({
      ok: false,
      status: 422,
      json: async () => ({ detail: "The PDF contains no extractable text." }),
    });

    await expect(extractFile(new Blob(["x"]), "scan.pdf")).rejects.toThrow(
      "The PDF contains no extractable text.",
    );
  });

  it("falls back to a status-based message when the error body is not JSON", async () => {
    stubFetch({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error("not json");
      },
    });

    await expect(extractFile(new Blob(["x"]), "note.webm")).rejects.toThrow("HTTP 502");
  });

  it("reports an unreachable backend in plain language", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(extractFile(new Blob(["x"]), "claim.png")).rejects.toThrow(
      "Could not reach the backend",
    );
  });
});

describe("describeExtractFailure", () => {
  it("prefers the backend detail when present", () => {
    expect(describeExtractFailure(413, "Request body too large.")).toBe("Request body too large.");
  });

  it.each([
    [413, /too large/],
    [415, /Unsupported file type/],
    [429, /Too many requests/],
    [503, /provider key/],
    [500, /HTTP 500/],
  ])("maps HTTP %i to a readable sentence", (status, expected) => {
    expect(describeExtractFailure(status)).toMatch(expected);
  });
});
