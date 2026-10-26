import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ApiError, Persona, TurnDetail, listSessionTurns, turnAudioUrl } from "../api";
import ChatAudioButton from "./ChatAudioButton";

export default function ChatHistorySessionPage() {
  const persona = useOutletContext<Persona>();
  const { sessionId } = useParams<{ sessionId: string }>();
  const [turns, setTurns] = useState<TurnDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    listSessionTurns(sessionId)
      .then(setTurns)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load that conversation."))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div>
      <div className="section-intro">
        <Link className="workspace-header__back" to="..">
          &larr; all conversations
        </Link>
        <h2 style={{ marginTop: "0.9rem" }}>Conversation with {persona.name}</h2>
        {sessionId && (
          <Link className="btn btn--primary" style={{ marginTop: "0.9rem" }} to={`/personas/${persona.id}/call?session=${sessionId}`}>
            Continue this conversation &rarr;
          </Link>
        )}
      </div>

      {error && <div className="error-banner" style={{ marginTop: "1.25rem" }}>{error}</div>}

      {loading && <p className="empty-note">Loading…</p>}

      {!loading && turns.length > 0 && sessionId && (
        <div className="transcript" style={{ marginTop: "1.75rem" }}>
          {turns.map((t) => (
            <div key={t.id} className={`transcript-line transcript-line--${t.role}`}>
              <span className="transcript-line__speaker">{t.role === "user" ? "You" : persona.name}</span>
              <span className={`transcript-line__text ${t.has_audio ? "transcript-line__text--has-audio" : ""}`}>
                {t.text}
                {t.has_audio && <ChatAudioButton src={turnAudioUrl(sessionId, t.id)} />}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
