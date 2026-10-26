import { useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { ApiError, Persona, addPerson } from "../api";

export default function AddPersonPage() {
  const persona = useOutletContext<Persona>();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [relationToPersona, setRelationToPersona] = useState("");
  const [relationToUser, setRelationToUser] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await addPerson(persona.id, {
        name: name.trim(),
        relation_to_persona: relationToPersona.trim(),
        relation_to_user: relationToUser.trim(),
        notes: notes.trim(),
      });
      navigate("..", { relative: "path" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save that person. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div>
      <Link className="workspace-header__back" to="..">
        &larr; {persona.name}'s people
      </Link>

      <div className="section-intro" style={{ marginTop: "1.1rem" }}>
        <h2>Add a person</h2>
        <p>Someone in {persona.name}'s life, and how they're related — to {persona.name} and to you.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="memory-form" onSubmit={handleAdd}>
        <div className="field">
          <label htmlFor="person-name">Name</label>
          <input
            id="person-name"
            type="text"
            placeholder="e.g. Priya"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <div className="field">
          <label htmlFor="person-relation-persona">Relation to {persona.name}</label>
          <input
            id="person-relation-persona"
            type="text"
            placeholder="e.g. daughter, best friend, neighbor"
            value={relationToPersona}
            onChange={(e) => setRelationToPersona(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="person-relation-user">Relation to you</label>
          <input
            id="person-relation-user"
            type="text"
            placeholder="e.g. my sister, my mom's friend"
            value={relationToUser}
            onChange={(e) => setRelationToUser(e.target.value)}
          />
        </div>
        <textarea
          rows={4}
          placeholder="Anything else worth remembering about this relationship (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <button className="btn btn--primary memory-form__submit" type="submit" disabled={busy || !name.trim()}>
          {busy ? "Saving…" : "Add person"}
        </button>
      </form>
    </div>
  );
}
