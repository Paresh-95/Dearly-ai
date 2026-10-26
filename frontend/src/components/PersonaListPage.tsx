import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, Persona, listPersonas } from "../api";
import PersonaAvatar from "./PersonaAvatar";

export default function PersonaListPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPersonas()
      .then(setPersonas)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load personas."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="picker-intro">
        <h1>Who are you missing?</h1>
        <p>Choose someone to continue with, or start with someone new.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!loading && (
        <div className="profile-grid">
          {personas.map((p) => (
            <Link key={p.id} className="profile-tile" to={`/personas/${p.id}`}>
              <PersonaAvatar persona={p} size={112} />
              <span className="profile-tile__name">{p.name}</span>
              {p.relationship_to_user && (
                <span className="profile-tile__relationship">{p.relationship_to_user}</span>
              )}
            </Link>
          ))}

          <Link className="profile-tile profile-tile--add" to="/new">
            <span className="profile-tile__add-icon" style={{ width: 112, height: 112 }}>
              +
            </span>
            <span className="profile-tile__name">Someone new</span>
          </Link>
        </div>
      )}
    </div>
  );
}
