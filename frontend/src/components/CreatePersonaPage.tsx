import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, Gender, PersonaLanguage, createPersona } from "../api";
import { inferReverseRelation } from "../utils/relations";

export default function CreatePersonaPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [gender, setGender] = useState<Gender | "">("");
  const [userRelationship, setUserRelationship] = useState("");
  const [userRelationshipTouched, setUserRelationshipTouched] = useState(false);
  const [userGender, setUserGender] = useState<Gender | "">("");

  function handleRelationshipBlur() {
    if (userRelationshipTouched || userRelationship.trim()) return;
    const guess = inferReverseRelation(relationship);
    if (guess) setUserRelationship(guess);
  }
  const [tone, setTone] = useState("");
  const [quirks, setQuirks] = useState("");
  const [exampleMessages, setExampleMessages] = useState("");
  const [language, setLanguage] = useState<PersonaLanguage>("en");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const persona = await createPersona({
        name: name.trim(),
        relationship_to_user: relationship.trim(),
        gender: gender || null,
        user_relationship: userRelationship.trim(),
        user_gender: userGender || null,
        personality_notes: { tone, quirks, example_messages: exampleMessages.trim() },
        language,
      });
      navigate(`/personas/${persona.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create that persona. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div>
      <Link className="workspace-header__back" to="/">
        &larr; all personas
      </Link>

      <div className="picker-intro">
        <h1>Let's bring them back into the room.</h1>
        <p>
          Start with who you're missing. A few details about them — their name, how they spoke,
          the small things only you would notice — are enough to begin.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="create-form" onSubmit={handleCreate}>
        <div className="field">
          <label htmlFor="persona-name">Their name</label>
          <input
            id="persona-name"
            type="text"
            placeholder="e.g. Nasreen"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="persona-relationship">Who they were to you</label>
          <input
            id="persona-relationship"
            type="text"
            placeholder="e.g. my mother, my partner, my oldest friend"
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            onBlur={handleRelationshipBlur}
          />
        </div>
        <div className="field">
          <label htmlFor="persona-gender">Their gender</label>
          <select
            id="persona-gender"
            value={gender}
            onChange={(e) => setGender(e.target.value as Gender | "")}
          >
            <option value="">Prefer not to say</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
          <p className="field-hint">Used for correct grammar in languages like Marathi — e.g. how they'd say "I went" changes by gender.</p>
        </div>
        <div className="field">
          <label htmlFor="persona-user-relationship">Who you are to them</label>
          <input
            id="persona-user-relationship"
            type="text"
            placeholder="e.g. their daughter, their grandson, their best friend"
            value={userRelationship}
            onChange={(e) => {
              setUserRelationshipTouched(true);
              setUserRelationship(e.target.value);
            }}
          />
          <p className="field-hint">Filled in automatically from who they were to you — edit if it's not quite right.</p>
        </div>
        <div className="field">
          <label htmlFor="persona-user-gender">Your gender</label>
          <select
            id="persona-user-gender"
            value={userGender}
            onChange={(e) => setUserGender(e.target.value as Gender | "")}
          >
            <option value="">Prefer not to say</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
          <p className="field-hint">So they address you correctly — e.g. how they'd say "you did" changes by gender in Marathi.</p>
        </div>
        <div className="field">
          <label htmlFor="persona-tone">How they came across</label>
          <input
            id="persona-tone"
            type="text"
            placeholder="e.g. warm, a little teasing, endlessly patient"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="persona-quirks">Phrases or quirks that were only theirs</label>
          <input
            id="persona-quirks"
            type="text"
            placeholder="e.g. called everyone 'love', always said 'well, anyway'"
            value={quirks}
            onChange={(e) => setQuirks(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="persona-examples">Real texts or messages from them (optional)</label>
          <textarea
            id="persona-examples"
            rows={5}
            placeholder={"Paste a handful of real texts, exactly as they wrote them — this is the best way to capture how they actually sounded.\ne.g.\nlol ok fine ill come\nomw give me 10 min\nyou good? that sounded rough"}
            value={exampleMessages}
            onChange={(e) => setExampleMessages(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="persona-language">Language they'll talk with you in</label>
          <select
            id="persona-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as PersonaLanguage)}
          >
            <option value="en">English</option>
            <option value="mr">Marathi</option>
          </select>
        </div>
        <button className="btn btn--primary" type="submit" disabled={busy || !name.trim()}>
          {busy ? "Creating…" : "Begin"}
        </button>
      </form>

      <p className="field-hint" style={{ marginTop: "1.25rem" }}>
        You can add their photo, memories, and voice once they're created.
      </p>
    </div>
  );
}
