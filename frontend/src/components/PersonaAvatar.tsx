import { Persona, personaPhotoUrl } from "../api";

export default function PersonaAvatar({ persona, size = 44 }: { persona: Persona; size?: number }) {
  const initial = persona.name.trim().slice(0, 1).toUpperCase() || "?";

  if (persona.has_photo) {
    return (
      <img
        className="persona-avatar"
        src={personaPhotoUrl(persona.id)}
        crossOrigin="use-credentials"
        alt={persona.name}
        style={{ width: size, height: size, fontSize: size * 0.42 }}
      />
    );
  }

  return (
    <div className="persona-avatar persona-avatar--fallback" style={{ width: size, height: size, fontSize: size * 0.42 }}>
      {initial}
    </div>
  );
}
