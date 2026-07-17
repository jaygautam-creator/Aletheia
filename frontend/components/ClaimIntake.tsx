"use client";

// The multimodal claim-intake row (ADR-0009): bring the claim as a PDF, a photo, or a
// voice note. Whatever is extracted lands in the *editable* query field via onText —
// the user reviews it before verifying; nothing is submitted automatically.

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { extractFile } from "@/lib/extract";

const MAX_RECORDING_SECONDS = 60;

const CHIP =
  "group flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1.5 text-xs text-slate-600 transition hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-40";

type Working = "pdf" | "image" | "audio" | "recording" | null;

const WORKING_LABEL: Record<Exclude<Working, "recording" | null>, string> = {
  pdf: "Reading the PDF…",
  image: "Reading the image…",
  audio: "Transcribing…",
};

function audioFilename(mimeType: string): string {
  if (mimeType.includes("mp4")) return "note.mp4";
  if (mimeType.includes("ogg")) return "note.ogg";
  return "note.webm";
}

// Microphone support is a static, client-only fact: false on the server (so SSR and
// the first client render agree), probed once in the browser. Nothing to subscribe to.
const subscribeToNothing = () => () => {};
const canRecordSnapshot = () =>
  typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);
const canRecordOnServer = () => false;

export function ClaimIntake({
  onText,
  disabled = false,
  label = "Or bring the claim as a file",
}: {
  onText: (text: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const [working, setWorking] = useState<Working>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const pdfInput = useRef<HTMLInputElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const audioInput = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);

  // Without microphone support, voice falls back to a plain audio-file picker.
  const canRecord = useSyncExternalStore(subscribeToNothing, canRecordSnapshot, canRecordOnServer);

  // Recording clock: tick once a second and auto-stop at the cap so a forgotten
  // microphone can't produce an oversized upload (or an oversized Whisper bill).
  useEffect(() => {
    if (working !== "recording") return;
    const id = setInterval(() => {
      setSeconds((current) => {
        if (current + 1 >= MAX_RECORDING_SECONDS) stopRecording();
        return current + 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [working]);

  async function handleUpload(kind: Exclude<Working, "recording" | null>, file: Blob, name: string) {
    setWorking(kind);
    setError(null);
    setNotice(null);
    try {
      const result = await extractFile(file, name);
      onText(result.text);
      if (result.truncated) {
        setNotice(
          "Long document — only the beginning was brought in. Trim it down to the claim you want checked.",
        );
      }
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Extraction failed.");
    } finally {
      setWorking(null);
    }
  }

  function onFileChosen(
    kind: Exclude<Working, "recording" | null>,
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file
    if (file) void handleUpload(kind, file, file.name);
  }

  async function startRecording() {
    setError(null);
    setNotice(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access was denied — allow it, or upload an audio file instead.");
      return;
    }
    // Chrome/Firefox record webm; Safari records mp4 via its default type.
    const preferred = MediaRecorder.isTypeSupported?.("audio/webm") ? "audio/webm" : undefined;
    const recorder = new MediaRecorder(stream, preferred ? { mimeType: preferred } : undefined);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      const type = recorder.mimeType || "audio/webm";
      void handleUpload("audio", new Blob(chunks, { type }), audioFilename(type));
    };
    recorderRef.current = recorder;
    recorder.start();
    setSeconds(0);
    setWorking("recording");
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    recorderRef.current = null;
  }

  const busy = working !== null && working !== "recording";
  const blocked = disabled || busy;

  return (
    <div className="flex flex-col gap-2">
      <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => pdfInput.current?.click()}
          disabled={blocked || working === "recording"}
          className={CHIP}
        >
          PDF
        </button>
        <input
          ref={pdfInput}
          type="file"
          accept="application/pdf"
          aria-label="Upload a PDF"
          className="hidden"
          onChange={(event) => onFileChosen("pdf", event)}
        />

        <button
          type="button"
          onClick={() => imageInput.current?.click()}
          disabled={blocked || working === "recording"}
          className={CHIP}
        >
          Photo
        </button>
        <input
          ref={imageInput}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          aria-label="Upload an image"
          className="hidden"
          onChange={(event) => onFileChosen("image", event)}
        />

        {canRecord ? (
          working === "recording" ? (
            <button
              type="button"
              onClick={stopRecording}
              className="flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-600 transition hover:border-rose-300"
            >
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
              Stop ({MAX_RECORDING_SECONDS - seconds}s left)
            </button>
          ) : (
            <button type="button" onClick={() => void startRecording()} disabled={blocked} className={CHIP}>
              Voice
            </button>
          )
        ) : (
          <>
            <button
              type="button"
              onClick={() => audioInput.current?.click()}
              disabled={blocked}
              className={CHIP}
            >
              Voice
            </button>
            <input
              ref={audioInput}
              type="file"
              accept="audio/*"
              aria-label="Upload an audio recording"
              className="hidden"
              onChange={(event) => onFileChosen("audio", event)}
            />
          </>
        )}

        {working !== null && working !== "recording" && (
          <span className="text-xs text-slate-500" role="status">
            {WORKING_LABEL[working]}
          </span>
        )}
      </div>
      {error && (
        <p className="text-xs text-rose-600" role="alert">
          {error}
        </p>
      )}
      {notice && <p className="text-xs text-slate-500">{notice}</p>}
    </div>
  );
}
