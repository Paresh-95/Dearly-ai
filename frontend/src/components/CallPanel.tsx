import { FormEvent, useEffect, useRef, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import {
  ApiError,
  Persona,
  createSession,
  listSessionTurns,
  sendTextTurn,
  sendTurn,
  turnAudioUrl,
} from "../api";
import ChatAudioButton from "./ChatAudioButton";
import Toast from "./Toast";

type ChatLine = { role: "user" | "assistant"; text: string; audioUrl?: string; autoPlay?: boolean };

export default function CallPanel() {
  const persona = useOutletContext<Persona>();
  const [searchParams] = useSearchParams();
  const continueSessionId = searchParams.get("session");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(!!continueSessionId);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (!continueSessionId) return;
    setSessionId(continueSessionId);
    listSessionTurns(continueSessionId)
      .then((turns) => {
        setLines(
          turns.map((t) => ({
            role: t.role,
            text: t.text,
            audioUrl: t.has_audio ? turnAudioUrl(continueSessionId, t.id) : undefined,
          }))
        );
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load that conversation."))
      .finally(() => setLoadingHistory(false));
    // Only re-run if the session being continued actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [continueSessionId]);

  async function ensureSession() {
    if (sessionId) return sessionId;
    const session = await createSession(persona.id);
    setSessionId(session.id);
    return session.id;
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.onstop = () => stream.getTracks().forEach((t) => t.stop());
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }

  async function stopRecordingAndSend() {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    setRecording(false);

    const stopped = new Promise<void>((resolve) => {
      recorder.onstop = () => resolve();
    });
    recorder.stop();
    await stopped;

    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    setBusy(true);
    setError(null);
    try {
      const sid = await ensureSession();
      const result = await sendTurn(sid, blob);
      setLines((prev) => [
        ...prev,
        { role: "user", text: result.transcript },
        {
          role: "assistant",
          text: result.reply_text,
          audioUrl: result.has_audio ? turnAudioUrl(sid, result.turn_id) : undefined,
          autoPlay: true,
        },
      ]);
      if (result.audio_error) setNotice(result.audio_error);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send that. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function sendTextMessage(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;

    setDraft("");
    setBusy(true);
    setError(null);
    try {
      const sid = await ensureSession();
      const result = await sendTextTurn(sid, text);
      setLines((prev) => [
        ...prev,
        { role: "user", text: result.transcript },
        {
          role: "assistant",
          text: result.reply_text,
          audioUrl: result.has_audio ? turnAudioUrl(sid, result.turn_id) : undefined,
          autoPlay: true,
        },
      ]);
      if (result.audio_error) setNotice(result.audio_error);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send that. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!persona.has_voice) {
    return (
      <div className="call-notice">
        Before you can call {persona.name}, clone their voice on the "Voice samples" tab — it only
        takes a few clips.
      </div>
    );
  }

  const orbState = recording ? "recording" : busy ? "thinking" : "idle";
  const statusText =
    orbState === "recording"
      ? "Listening — tap again when you're done"
      : orbState === "thinking"
      ? `${persona.name} is finding the words…`
      : "Tap to speak";

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      {notice && <Toast message={notice} onDismiss={() => setNotice(null)} />}

      <div className="call-stage">
        <div className="call-stage__name">
          You're speaking with <strong>{persona.name}</strong>
        </div>

        <button
          className={`orb-button ${orbState === "recording" ? "orb-button--recording" : ""} ${
            orbState === "thinking" ? "orb-button--thinking" : ""
          }`}
          onClick={recording ? stopRecordingAndSend : startRecording}
          disabled={busy}
          aria-label={orbState === "recording" ? "Stop and send" : "Start speaking"}
        >
          {orbState === "recording" && (
            <>
              <span className="orb-ring" />
              <span className="orb-ring orb-ring--delay" />
            </>
          )}
          {orbState === "thinking" ? (
            <span className="orb-dots">
              <span />
              <span />
              <span />
            </span>
          ) : (
            <MicIcon muted={orbState === "recording"} />
          )}
        </button>

        <div className="call-stage__status">{statusText}</div>
      </div>

      <form className="call-text-form" onSubmit={sendTextMessage}>
        <input
          type="text"
          className="call-text-form__input"
          placeholder={`Type a message to ${persona.name}…`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={busy || recording}
          maxLength={4000}
        />
        <button
          type="submit"
          className="call-text-form__send"
          disabled={busy || recording || !draft.trim()}
        >
          Send
        </button>
      </form>

      {loadingHistory && <p className="empty-note">Loading the rest of this conversation…</p>}

      {lines.length > 0 && (
        <div className="transcript">
          {lines.map((line, i) => (
            <div key={i} className={`transcript-line transcript-line--${line.role}`}>
              <span className="transcript-line__speaker">{line.role === "user" ? "You" : persona.name}</span>
              <span className={`transcript-line__text ${line.audioUrl ? "transcript-line__text--has-audio" : ""}`}>
                {line.text}
                {line.audioUrl && <ChatAudioButton src={line.audioUrl} autoPlay={line.autoPlay} />}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MicIcon({ muted }: { muted: boolean }) {
  return (
    <svg className="orb-button__icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 15a3.5 3.5 0 0 0 3.5-3.5v-5a3.5 3.5 0 0 0-7 0v5A3.5 3.5 0 0 0 12 15Z"
        stroke={muted ? "#fdfbf8" : "#4a3620"}
        strokeWidth="1.6"
      />
      <path
        d="M6.5 11v.5a5.5 5.5 0 0 0 11 0V11M12 17v2.5"
        stroke={muted ? "#fdfbf8" : "#4a3620"}
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
