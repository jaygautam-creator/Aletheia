// Framework-agnostic types and reducers for the streamed verification path.
//
// These mirror the backend's /verify/stream Server-Sent Events: one event per graph node
// carrying that stage's partial result. The parsing and state-folding here are pure, so
// they are unit-tested without React or a network; the hook in useVerificationStream wires
// them to fetch + a streaming response body.

export type Verdict = "Supported" | "Contradicted" | "Unverifiable";
export type Advisory = "info" | "caution" | "high_caution";

export interface Citation {
  index: number;
  title: string;
  connector: string;
  external_id: string;
  url: string | null;
  trust_tier: string;
  score: number;
}

export interface ClaimVerdict {
  claim: string;
  verdict: Verdict;
  quoted_span: string | null;
  reasoning: string;
}

export interface VerificationResultData {
  query: string;
  candidate_answer: string;
  verdicts: ClaimVerdict[];
  has_unsupported_claims: boolean;
  support_ratio: number;
  // Set by the intake guard when a query is declined (out of scope or a blocked
  // injection attempt); the pipeline did not generate an answer.
  refused?: boolean;
  refusal_reason?: string | null;
}

export interface SafetyAssessment {
  advisory: Advisory;
  disclaimer: string;
  notes: string[];
}

/** The (partial) JSON payload carried by one stage event. */
export interface StagePayload {
  citations?: Citation[];
  candidate_answer?: string;
  claims?: string[];
  verdicts?: ClaimVerdict[];
  result?: VerificationResultData;
  safety?: SafetyAssessment;
  detail?: string;
}

/** One Server-Sent Event: its name (stage / "done" / "error") and parsed data. */
export interface StreamEvent {
  event: string;
  data: StagePayload;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface StreamState {
  status: StreamStatus;
  stages: string[];
  citations: Citation[];
  candidateAnswer: string | null;
  claims: string[];
  verdicts: ClaimVerdict[];
  result: VerificationResultData | null;
  safety: SafetyAssessment | null;
  error: string | null;
}

export const initialStreamState: StreamState = {
  status: "idle",
  stages: [],
  citations: [],
  candidateAnswer: null,
  claims: [],
  verdicts: [],
  result: null,
  safety: null,
  error: null,
};

/**
 * Extract complete SSE frames from a text buffer.
 *
 * Frames are separated by a blank line; a trailing partial frame is returned as `rest`
 * so the caller can prepend it to the next chunk.
 */
export function parseSSE(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  const frames = buffer.split("\n\n");
  const rest = frames.pop() ?? "";
  for (const frame of frames) {
    if (!frame.trim()) continue;
    let event = "message";
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice("event:".length).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice("data:".length).trim());
    }
    let data: StagePayload = {};
    const dataText = dataLines.join("\n");
    if (dataText) {
      try {
        data = JSON.parse(dataText) as StagePayload;
      } catch {
        data = {};
      }
    }
    events.push({ event, data });
  }
  return { events, rest };
}

/** Fold one stream event into the accumulated state. Pure. */
export function applyEvent(state: StreamState, { event, data }: StreamEvent): StreamState {
  if (event === "error") {
    return { ...state, status: "error", error: data.detail ?? "stream error" };
  }
  if (event === "done") {
    return { ...state, status: "done" };
  }
  const next: StreamState = { ...state, status: "streaming", stages: [...state.stages, event] };
  if (data.citations) next.citations = data.citations;
  if (data.candidate_answer !== undefined) next.candidateAnswer = data.candidate_answer;
  if (data.claims) next.claims = data.claims;
  if (data.verdicts) next.verdicts = data.verdicts;
  if (data.result) next.result = data.result;
  if (data.safety) next.safety = data.safety;
  return next;
}
