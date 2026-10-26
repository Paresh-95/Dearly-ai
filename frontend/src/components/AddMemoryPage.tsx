import { useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { ApiError, Memory, Persona, addMemory } from "../api";

export default function AddMemoryPage() {
  const persona = useOutletContext<Persona>();
  const navigate = useNavigate();
  const [type, setType] = useState<Memory["type"]>("story");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await addMemory(persona.id, { type, raw_text: text.trim() });
      navigate("..", { relative: "path" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save that memory. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div>
      <Link className="workspace-header__back" to="..">
        &larr; {persona.name}'s memories
      </Link>

      <div className="section-intro" style={{ marginTop: "1.1rem" }}>
        <h2>Add a memory</h2>
        <p>Write it the way you'd tell it to someone else. A story, a habit, a line they loved to say.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="memory-form" onSubmit={handleAdd}>
        <div className="memory-form__row">
          <div className="field" style={{ flex: "0 0 auto" }}>
            <label htmlFor="memory-type">Kind of memory</label>
            <select id="memory-type" value={type} onChange={(e) => setType(e.target.value as Memory["type"])}>
              <option value="story">Story</option>
              <option value="fact">Fact</option>
              <option value="trait">Personality trait</option>
              <option value="quote">Thing they used to say</option>
              <option value="value">Something they valued</option>
              <option value="routine">Routine or ritual</option>
              <option value="preference">Preference (liked/disliked)</option>
              <option value="physical_detail">Physical/sensory detail</option>
              <option value="advice">Advice or life lesson</option>
              <option value="regret">Regret or unfinished business</option>
              <option value="timeline_event">Timeline event</option>
            </select>
          </div>
        </div>
        <textarea
          rows={6}
          placeholder="Write it the way you'd tell it to someone else…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />
        <button className="btn btn--primary memory-form__submit" type="submit" disabled={busy || !text.trim()}>
          {busy ? "Saving…" : "Add memory"}
        </button>
      </form>
    </div>
  );
}
