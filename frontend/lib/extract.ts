// Claim-intake extraction client for POST /extract: upload one PDF, image, or voice
// note and get back the plain text it contains. The caller places that text in the
// *editable* query field — extraction never verifies anything (ADR-0009).

export type ExtractKind = "pdf" | "image" | "audio";

export interface ExtractResponse {
  kind: ExtractKind;
  text: string;
  characters: number;
  truncated: boolean;
}

const EXTRACT_URL = `${process.env.NEXT_PUBLIC_API_URL ?? ""}/extract`;

/** Map an /extract failure to a sentence the intake row can show as-is. */
export function describeExtractFailure(status: number, detail?: string): string {
  if (detail) return detail;
  if (status === 413) return "That file is too large for the upload cap.";
  if (status === 415)
    return "Unsupported file type — use a PDF, a PNG/JPEG/WebP image, or an audio recording.";
  if (status === 429) return "Too many requests — wait a moment and try again.";
  if (status === 503) return "The backend is missing the provider key for this file type.";
  return `Extraction failed (HTTP ${status}).`;
}

/** Upload one file to /extract and return the text found in it. Throws with a readable message. */
export async function extractFile(file: Blob, filename: string): Promise<ExtractResponse> {
  const body = new FormData();
  body.append("file", file, filename);

  let response: Response;
  try {
    // No Content-Type header: the browser sets the multipart boundary itself.
    response = await fetch(EXTRACT_URL, { method: "POST", body, credentials: "include" });
  } catch {
    throw new Error("Could not reach the backend — is it running?");
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      detail = ((await response.json()) as { detail?: string }).detail;
    } catch {
      // Non-JSON error body: fall through to the status-based message.
    }
    throw new Error(describeExtractFailure(response.status, detail));
  }
  return (await response.json()) as ExtractResponse;
}
