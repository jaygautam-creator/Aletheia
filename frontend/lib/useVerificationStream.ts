"use client";

import { useCallback, useReducer, useRef } from "react";

import {
  applyEvent,
  initialStreamState,
  parseSSE,
  type StreamEvent,
  type StreamState,
} from "@/lib/verification";

export interface VerifyRequest {
  query: string;
  evidence?: string;
  candidate_answer?: string;
}

const STREAM_URL = `${process.env.NEXT_PUBLIC_API_URL ?? ""}/verify/stream`;

type Action = { type: "reset" } | { type: "event"; event: StreamEvent };

function reducer(state: StreamState, action: Action): StreamState {
  if (action.type === "reset") {
    return { ...initialStreamState, status: "streaming" };
  }
  return applyEvent(state, action.event);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "request failed";
}

/**
 * Drive the streamed verification path: POST the request to /verify/stream and fold the
 * Server-Sent Events into a single accumulating state for the UI to render live.
 */
export function useVerificationStream(): {
  state: StreamState;
  start: (request: VerifyRequest) => Promise<void>;
} {
  const [state, dispatch] = useReducer(reducer, initialStreamState);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (request: VerifyRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    dispatch({ type: "reset" });

    let response: Response;
    try {
      response = await fetch(STREAM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
    } catch (error) {
      dispatch({ type: "event", event: { event: "error", data: { detail: errorMessage(error) } } });
      return;
    }

    if (!response.ok || !response.body) {
      dispatch({
        type: "event",
        event: { event: "error", data: { detail: `request failed (HTTP ${response.status})` } },
      });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let done = false;
    try {
      while (!done) {
        const chunk = await reader.read();
        done = chunk.done;
        if (chunk.value) {
          buffer += decoder.decode(chunk.value, { stream: true });
          const parsed = parseSSE(buffer);
          buffer = parsed.rest;
          for (const event of parsed.events) {
            dispatch({ type: "event", event });
          }
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        dispatch({
          type: "event",
          event: { event: "error", data: { detail: errorMessage(error) } },
        });
      }
    }
  }, []);

  return { state, start };
}
