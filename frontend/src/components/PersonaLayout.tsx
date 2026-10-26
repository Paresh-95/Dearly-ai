import { useEffect, useState } from "react";
import { Link, Outlet, useMatch, useNavigate, useParams } from "react-router-dom";
import { ApiError, Persona, deletePersona, getPersona, uploadPersonaPhoto } from "../api";
import PersonaAvatar from "./PersonaAvatar";

export default function PersonaLayout() {
  const { personaId } = useParams<{ personaId: string }>();
  const navigate = useNavigate();
  const onCallTab = !!useMatch("/personas/:personaId/call");
  const onHistorySession = !!useMatch("/personas/:personaId/history/:sessionId");
  const [persona, setPersona] = useState<Persona | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);

  useEffect(() => {
    if (!personaId) return;
    setLoading(true);
    getPersona(personaId)
      .then(setPersona)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load that persona."))
      .finally(() => setLoading(false));
  }, [personaId]);

  async function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !personaId) return;
    setPhotoBusy(true);
    setError(null);
    try {
      const updated = await uploadPersonaPhoto(personaId, file);
      setPersona(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not upload that photo. Please try again.");
    } finally {
      setPhotoBusy(false);
      e.target.value = "";
    }
  }

  async function handleDelete() {
    if (!personaId) return;
    setDeleteBusy(true);
    try {
      await deletePersona(personaId);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove that persona. Please try again.");
      setDeleteBusy(false);
      setConfirmingDelete(false);
    }
  }

  if (loading) {
    return <p className="empty-note">Loading…</p>;
  }

  if (error && !persona) {
    return <div className="error-banner">{error}</div>;
  }

  if (!persona) {
    return null;
  }

  return (
    <div>
      <div className="workspace-header">
        {!onHistorySession && (
          <Link className="workspace-header__back" to="/">
            &larr; all personas
          </Link>
        )}

        <div className="workspace-header__identity">
          <label className="persona-avatar-upload" title="Change photo">
            <PersonaAvatar persona={persona} size={44} />
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/*" onChange={handlePhotoChange} disabled={photoBusy} />
          </label>
          <div>
            <h2 className="workspace-header__name">{persona.name}</h2>
            {persona.relationship_to_user && (
              <div className="workspace-header__relationship">{persona.relationship_to_user}</div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <Outlet context={persona} />

      <div className="persona-footer-row">
        <button className="btn btn--danger-outline" onClick={() => setConfirmingDelete(true)}>
          Remove {persona.name}
        </button>

        {onCallTab && (
          <Link className="btn--text" to="history">
            Chat history &rarr;
          </Link>
        )}
      </div>

      {confirmingDelete && (
        <div className="modal-overlay" onClick={() => !deleteBusy && setConfirmingDelete(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Remove {persona.name}?</h3>
            <p>Everything saved about them — memories, voice samples, conversations — will be gone for good. This can't be undone.</p>
            <div className="modal-card__actions">
              <button className="btn btn--quiet" onClick={() => setConfirmingDelete(false)} disabled={deleteBusy}>
                Cancel
              </button>
              <button className="btn btn--danger-outline" onClick={handleDelete} disabled={deleteBusy}>
                {deleteBusy ? "Removing…" : `Yes, remove ${persona.name}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
