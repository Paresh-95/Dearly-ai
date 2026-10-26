import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { ApiError, Memory, Persona, deleteMemory, listMemories, updateMemory } from "../api";

const TYPE_LABEL: Record<Memory["type"], string> = {
  story: "A story",
  fact: "A fact",
  trait: "A trait",
  quote: "Something they said",
  value: "Something they valued",
  routine: "A routine or ritual",
  preference: "A preference (liked/disliked)",
  physical_detail: "A physical/sensory detail",
  advice: "Advice or a life lesson",
  regret: "A regret or unfinished business",
  timeline_event: "A timeline event",
};

const TYPE_OPTIONS: Memory["type"][] = [
  "story",
  "fact",
  "trait",
  "quote",
  "value",
  "routine",
  "preference",
  "physical_detail",
  "advice",
  "regret",
  "timeline_event",
];

export default function MemoriesListPage() {
  const persona = useOutletContext<Persona>();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftType, setDraftType] = useState<Memory["type"]>("story");
  const [draftText, setDraftText] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);

  async function refresh() {
    setMemories(await listMemories(persona.id));
  }

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load memories."))
      .finally(() => setLoading(false));
  }, [persona.id]);

  function startEdit(m: Memory) {
    setEditingId(m.id);
    setDraftType(m.type);
    setDraftText(m.raw_text);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(memoryId: string) {
    if (!draftText.trim()) return;
    setSavingId(memoryId);
    setError(null);
    try {
      await updateMemory(persona.id, memoryId, { type: draftType, raw_text: draftText.trim() });
      setEditingId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save that change. Please try again.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div>
      <div className="section-intro">
        <h2>What do you remember?</h2>
        <p>Every story, fact, trait, and quote you've saved about {persona.name}.</p>
      </div>

      <Link className="btn btn--primary" to="new">
        Add a memory
      </Link>

      {error && <div className="error-banner" style={{ marginTop: "1.25rem" }}>{error}</div>}

      <div style={{ marginTop: "1.75rem" }}>
        {!loading && memories.length === 0 && !error && (
          <p className="empty-note">Nothing saved yet — add a memory above.</p>
        )}

        {memories.length > 0 && (
          <ul className="memory-list">
            {memories.map((m) =>
              editingId === m.id ? (
                <li key={m.id} className={`memory-card memory-card--${m.type}`}>
                  <div className="memory-card__body" style={{ width: "100%" }}>
                    <select
                      value={draftType}
                      onChange={(e) => setDraftType(e.target.value as Memory["type"])}
                      style={{ marginBottom: "0.5rem" }}
                    >
                      {TYPE_OPTIONS.map((t) => (
                        <option key={t} value={t}>
                          {TYPE_LABEL[t]}
                        </option>
                      ))}
                    </select>
                    <textarea
                      rows={4}
                      value={draftText}
                      onChange={(e) => setDraftText(e.target.value)}
                      style={{ width: "100%" }}
                    />
                    <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.6rem" }}>
                      <button
                        className="btn btn--primary btn--sm"
                        disabled={savingId === m.id || !draftText.trim()}
                        onClick={() => saveEdit(m.id)}
                      >
                        {savingId === m.id ? "Saving…" : "Save"}
                      </button>
                      <button className="btn btn--quiet btn--sm" disabled={savingId === m.id} onClick={cancelEdit}>
                        Cancel
                      </button>
                    </div>
                  </div>
                </li>
              ) : (
                <li key={m.id} className={`memory-card memory-card--${m.type}`}>
                  <div className="memory-card__body">
                    <div className="memory-card__type">{TYPE_LABEL[m.type]}</div>
                    <div className="memory-card__text">{m.raw_text}</div>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
                    <button className="btn btn--quiet btn--sm" onClick={() => startEdit(m)}>
                      edit
                    </button>
                    <button
                      className="btn btn--danger"
                      onClick={async () => {
                        await deleteMemory(persona.id, m.id);
                        await refresh();
                      }}
                    >
                      remove
                    </button>
                  </div>
                </li>
              )
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
