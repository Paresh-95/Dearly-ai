import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { ApiError, Persona, SessionSummary, listSessions } from "../api";

function formatStartedAt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function ChatHistoryPage() {
  const persona = useOutletContext<Persona>();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listSessions(persona.id)
      .then(setSessions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load chat history."))
      .finally(() => setLoading(false));
  }, [persona.id]);

  return (
    <div>
      <div className="section-intro">
        <h2>Past conversations</h2>
        <p>Every session you've had with {persona.name}, grouped by when it happened.</p>
      </div>

      {error && <div className="error-banner" style={{ marginTop: "1.25rem" }}>{error}</div>}

      <div style={{ marginTop: "1.75rem" }}>
        {!loading && sessions.length === 0 && !error && (
          <p className="empty-note">No conversations yet — say something on the Call tab to start one.</p>
        )}

        {sessions.length > 0 && (
          <ul className="memory-list">
            {sessions.map((s) => (
              <li key={s.id} className="memory-card">
                <Link to={s.id} className="memory-card__body session-card__link">
                  <div className="memory-card__type">
                    {formatStartedAt(s.started_at)} &middot; {s.turn_count} {s.turn_count === 1 ? "turn" : "turns"}
                  </div>
                  <div className="memory-card__text">{s.last_message ?? "(no messages)"}</div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
