import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { ApiError, Person, Persona, deletePerson, listPeople, updatePerson } from "../api";
import PeopleGraphView from "./PeopleGraphView";

type ViewMode = "list" | "graph";

export default function PeopleListPage() {
  const persona = useOutletContext<Persona>();
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("graph");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftRelationToPersona, setDraftRelationToPersona] = useState("");
  const [draftRelationToUser, setDraftRelationToUser] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);

  async function refresh() {
    setPeople(await listPeople(persona.id));
  }

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load people."))
      .finally(() => setLoading(false));
  }, [persona.id]);

  function startEdit(p: Person) {
    setEditingId(p.id);
    setDraftName(p.name);
    setDraftRelationToPersona(p.relation_to_persona);
    setDraftRelationToUser(p.relation_to_user);
    setDraftNotes(p.notes);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(personId: string) {
    if (!draftName.trim()) return;
    setSavingId(personId);
    setError(null);
    try {
      await updatePerson(persona.id, personId, {
        name: draftName.trim(),
        relation_to_persona: draftRelationToPersona.trim(),
        relation_to_user: draftRelationToUser.trim(),
        notes: draftNotes.trim(),
      });
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
        <h2>Who's in their life?</h2>
        <p>
          The people around {persona.name} — how each of them is related, so the AI can answer questions
          about who's who.
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <Link className="btn btn--primary" to="new">
          Add a person
        </Link>
        <div className="people-view-toggle">
          <button
            type="button"
            className={`people-view-toggle__btn ${view === "graph" ? "people-view-toggle__btn--active" : ""}`}
            onClick={() => setView("graph")}
          >
            Graph
          </button>
          <button
            type="button"
            className={`people-view-toggle__btn ${view === "list" ? "people-view-toggle__btn--active" : ""}`}
            onClick={() => setView("list")}
          >
            List
          </button>
        </div>
      </div>

      {error && <div className="error-banner" style={{ marginTop: "1.25rem" }}>{error}</div>}

      <div style={{ marginTop: "1.75rem" }}>
        {!loading && view === "graph" && <PeopleGraphView persona={persona} people={people} />}

        {!loading && people.length === 0 && view === "list" && !error && (
          <p className="empty-note">Nobody added yet — add a person above.</p>
        )}

        {people.length > 0 && view === "list" && (
          <ul className="memory-list">
            {people.map((p) =>
              editingId === p.id ? (
                <li key={p.id} className="memory-card">
                  <div className="memory-card__body" style={{ width: "100%" }}>
                    <input
                      type="text"
                      placeholder="Name"
                      value={draftName}
                      onChange={(e) => setDraftName(e.target.value)}
                      style={{ width: "100%", marginBottom: "0.5rem" }}
                    />
                    <input
                      type="text"
                      placeholder={`Relation to ${persona.name} (e.g. daughter, best friend)`}
                      value={draftRelationToPersona}
                      onChange={(e) => setDraftRelationToPersona(e.target.value)}
                      style={{ width: "100%", marginBottom: "0.5rem" }}
                    />
                    <input
                      type="text"
                      placeholder="Relation to you (e.g. my sister, mom's friend)"
                      value={draftRelationToUser}
                      onChange={(e) => setDraftRelationToUser(e.target.value)}
                      style={{ width: "100%", marginBottom: "0.5rem" }}
                    />
                    <textarea
                      rows={3}
                      placeholder="Anything else worth remembering about this relationship"
                      value={draftNotes}
                      onChange={(e) => setDraftNotes(e.target.value)}
                      style={{ width: "100%" }}
                    />
                    <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.6rem" }}>
                      <button
                        className="btn btn--primary btn--sm"
                        disabled={savingId === p.id || !draftName.trim()}
                        onClick={() => saveEdit(p.id)}
                      >
                        {savingId === p.id ? "Saving…" : "Save"}
                      </button>
                      <button className="btn btn--quiet btn--sm" disabled={savingId === p.id} onClick={cancelEdit}>
                        Cancel
                      </button>
                    </div>
                  </div>
                </li>
              ) : (
                <li key={p.id} className="memory-card">
                  <div className="memory-card__body">
                    <div className="memory-card__type">{p.name}</div>
                    <div className="memory-card__text">
                      {p.relation_to_persona && <div>{persona.name}'s {p.relation_to_persona}</div>}
                      {p.relation_to_user && <div>Your {p.relation_to_user}</div>}
                      {p.notes && <div>{p.notes}</div>}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
                    <button className="btn btn--quiet btn--sm" onClick={() => startEdit(p)}>
                      edit
                    </button>
                    <button
                      className="btn btn--danger"
                      onClick={async () => {
                        await deletePerson(persona.id, p.id);
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
