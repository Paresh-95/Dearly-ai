import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, AuthUser, approveUser, listPendingUsers } from "../api";

export default function AdminPanel() {
  const [pending, setPending] = useState<AuthUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setPending(await listPendingUsers());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load pending accounts.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleApprove(id: string) {
    setBusyId(id);
    try {
      await approveUser(id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve that account.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <Link className="workspace-header__back" to="/">
        &larr; all personas
      </Link>

      <div className="section-intro">
        <h2>Waiting for approval</h2>
        <p>New accounts stay out until you let them in.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <p className="empty-note">Loading…</p>
      ) : pending.length === 0 ? (
        <p className="empty-note">Nobody's waiting right now.</p>
      ) : (
        <ul className="persona-list">
          {pending.map((u) => (
            <li key={u.id} className="persona-row" style={{ cursor: "default" }}>
              <span className="persona-row__name">{u.email}</span>
              <button
                className="btn btn--primary"
                disabled={busyId === u.id}
                onClick={() => handleApprove(u.id)}
              >
                {busyId === u.id ? "Approving…" : "Approve"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
