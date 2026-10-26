import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { ApiError, Gender, Persona, PersonaLanguage, VoiceProvider, updatePersona } from "../api";

const PROVIDER_LABELS: Record<VoiceProvider, string> = {
  fish_audio: "Fish Audio",
  sarvam: "Sarvam AI",
};

export default function PersonaSettingsPage() {
  const outletPersona = useOutletContext<Persona>();
  const [persona, setPersona] = useState<Persona>(outletPersona);
  const notes = persona.personality_notes || {};

  const [name, setName] = useState(persona.name);
  const [relationship, setRelationship] = useState(persona.relationship_to_user);
  const [gender, setGender] = useState<Gender | "">(persona.gender ?? "");
  const [userRelationship, setUserRelationship] = useState(persona.user_relationship);
  const [userGender, setUserGender] = useState<Gender | "">(persona.user_gender ?? "");
  const [tone, setTone] = useState(notes.tone ?? "");
  const [quirks, setQuirks] = useState(notes.quirks ?? "");
  const [demeanor, setDemeanor] = useState(notes.demeanor ?? "");
  const [addressUserAs, setAddressUserAs] = useState(notes.address_user_as ?? "");
  const [exampleMessages, setExampleMessages] = useState(notes.example_messages ?? "");
  const [language, setLanguage] = useState<PersonaLanguage>(persona.language);

  const [busy, setBusy] = useState(false);
  const [providerBusy, setProviderBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePersona(persona.id, {
        name: name.trim(),
        relationship_to_user: relationship.trim(),
        gender: gender || null,
        user_relationship: userRelationship.trim(),
        user_gender: userGender || null,
        personality_notes: {
          tone,
          quirks,
          demeanor,
          address_user_as: addressUserAs,
          example_messages: exampleMessages.trim(),
        },
        language,
      });
      setPersona(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save those changes. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSwitchProvider(provider: VoiceProvider) {
    if (provider === persona.voice_provider) return;
    setProviderBusy(true);
    setError(null);
    try {
      setPersona(await updatePersona(persona.id, { voice_provider: provider }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not switch voice provider. Please try again.");
    } finally {
      setProviderBusy(false);
    }
  }

  return (
    <div>
      <div className="section-intro">
        <h2>Settings</h2>
        <p>Adjust how {persona.name} is set up — their details, how they talk, and which voice speaks for them.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="create-form" onSubmit={handleSave}>
        <div className="field">
          <label htmlFor="settings-name">Their name</label>
          <input id="settings-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="settings-relationship">Who they were to you</label>
          <input
            id="settings-relationship"
            type="text"
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-gender">Their gender</label>
          <select
            id="settings-gender"
            value={gender}
            onChange={(e) => setGender(e.target.value as Gender | "")}
          >
            <option value="">Prefer not to say</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
          <p className="field-hint">Used for correct grammar in languages like Marathi.</p>
        </div>
        <div className="field">
          <label htmlFor="settings-user-relationship">Who you are to them</label>
          <input
            id="settings-user-relationship"
            type="text"
            placeholder="e.g. their daughter, their grandson, their best friend"
            value={userRelationship}
            onChange={(e) => setUserRelationship(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-user-gender">Your gender</label>
          <select
            id="settings-user-gender"
            value={userGender}
            onChange={(e) => setUserGender(e.target.value as Gender | "")}
          >
            <option value="">Prefer not to say</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
          <p className="field-hint">So they address you correctly in languages like Marathi.</p>
        </div>
        <div className="field">
          <label htmlFor="settings-tone">How they came across</label>
          <input id="settings-tone" type="text" value={tone} onChange={(e) => setTone(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="settings-quirks">Phrases or quirks that were only theirs</label>
          <input id="settings-quirks" type="text" value={quirks} onChange={(e) => setQuirks(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="settings-demeanor">Demeanor</label>
          <input
            id="settings-demeanor"
            type="text"
            placeholder="e.g. loud and animated, always mid-story with his hands moving"
            value={demeanor}
            onChange={(e) => setDemeanor(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-nickname">Nickname they called you</label>
          <input
            id="settings-nickname"
            type="text"
            placeholder="e.g. bhidu, love, kiddo"
            value={addressUserAs}
            onChange={(e) => setAddressUserAs(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-examples">Real texts or messages from them</label>
          <textarea
            id="settings-examples"
            rows={5}
            value={exampleMessages}
            onChange={(e) => setExampleMessages(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-language">Language they'll talk with you in</label>
          <select
            id="settings-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as PersonaLanguage)}
          >
            <option value="en">English</option>
            <option value="mr">Marathi</option>
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <button className="btn btn--primary" type="submit" disabled={busy || !name.trim()}>
            {busy ? "Saving…" : "Save changes"}
          </button>
          {saved && <span className="clone-status__pill">Saved</span>}
        </div>
      </form>

      <div className="voice-provider-picker" style={{ marginTop: "2.25rem" }}>
        <h3 className="voice-provider-picker__title">Voice provider</h3>
        <p className="field-hint">
          Which service actually speaks for {persona.name}. Switching doesn't delete the other one's setup —
          clone/configure a voice for each provider independently on the "Voice samples" tab.
        </p>
        <div className="voice-provider-picker__options">
          {(["fish_audio", "sarvam"] as VoiceProvider[]).map((provider) => {
            const providerVoiceId = provider === "sarvam" ? persona.sarvam_voice_id : persona.provider_voice_id;
            const active = persona.voice_provider === provider;
            return (
              <button
                key={provider}
                type="button"
                className={`voice-provider-picker__option ${active ? "voice-provider-picker__option--active" : ""}`}
                disabled={providerBusy || active || !providerVoiceId}
                onClick={() => handleSwitchProvider(provider)}
                title={!providerVoiceId ? "No voice configured for this provider yet" : undefined}
              >
                {PROVIDER_LABELS[provider]}
                {active && <span className="voice-provider-picker__badge">active</span>}
                {!providerVoiceId && (
                  <span className="voice-provider-picker__badge voice-provider-picker__badge--muted">not set up</span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
