import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  ApiError,
  Persona,
  VoiceSample,
  cloneVoice,
  deleteVoiceSample,
  getPersona,
  listVoiceSamples,
  uploadVoiceSample,
  voiceSampleAudioUrl,
} from "../api";

export default function VoicePanel() {
  const outletPersona = useOutletContext<Persona>();
  const [persona, setPersona] = useState<Persona>(outletPersona);
  const [samples, setSamples] = useState<VoiceSample[]>([]);
  const [busy, setBusy] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setSamples(await listVoiceSamples(persona.id));
    // The persona prop can be stale (e.g. cloned from elsewhere since it was
    // loaded), so always re-check the real status from the backend.
    setPersona(await getPersona(persona.id));
  }

  useEffect(() => {
    refresh();
  }, [persona.id]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadVoiceSample(persona.id, file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not upload that file. Please try again.");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function handleDelete(sampleId: string) {
    setDeletingId(sampleId);
    setError(null);
    try {
      await deleteVoiceSample(persona.id, sampleId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete that sample. Please try again.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleClone() {
    setBusy(true);
    setError(null);
    try {
      const result = await cloneVoice(persona.id);
      setPersona((prev) => ({ ...prev, provider_voice_id: result.provider_voice_id }));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not clone the voice. Please try again.";
      setError(persona.provider_voice_id ? `${message} Still using the previously cloned voice.` : message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="section-intro">
        <h2>The sound of their voice</h2>
        <p>
          A few short, clear clips are enough — a voicemail, a video, anything where you can hear
          them clearly. Accepted formats: .mp3, .wav, .m4a.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="upload-dropzone">
        <input type="file" accept=".mp3,.wav,.m4a,audio/*" onChange={handleUpload} disabled={busy} />
        <span className="field-hint">
          {samples.length === 0 ? "No samples uploaded yet." : `${samples.length} sample${samples.length === 1 ? "" : "s"} uploaded.`}
        </span>
      </div>

      {samples.length > 0 && (
        <ul className="sample-list">
          {samples.map((s) => (
            <li key={s.id} className="sample-row">
              <span className="sample-row__dot" />
              <span className="sample-row__label">
                {s.duration_seconds != null ? `${Math.round(s.duration_seconds)}s clip` : "Voice clip"}
              </span>
              <audio controls src={voiceSampleAudioUrl(persona.id, s.id)} crossOrigin="use-credentials" />
              <button
                className="btn btn--danger btn--sm"
                disabled={deletingId === s.id}
                onClick={() => handleDelete(s.id)}
              >
                {deletingId === s.id ? "Removing…" : "remove"}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="clone-status">
        <button className="btn btn--primary" disabled={busy || samples.length === 0} onClick={handleClone}>
          {busy ? "Working…" : persona.provider_voice_id ? "Update their voice" : "Clone their voice"}
        </button>
        {persona.provider_voice_id && <span className="clone-status__pill">Voice ready</span>}
      </div>
    </div>
  );
}
