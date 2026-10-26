const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

export type PersonaLanguage = "en" | "mr";
export type VoiceProvider = "fish_audio" | "sarvam";
export type Gender = "male" | "female" | "other";

export interface Persona {
  id: string;
  name: string;
  relationship_to_user: string;
  gender: Gender | null;
  user_relationship: string;
  user_gender: Gender | null;
  personality_notes: Record<string, string>;
  language: PersonaLanguage;
  provider_voice_id: string | null;
  sarvam_voice_id: string | null;
  voice_provider: VoiceProvider;
  has_photo: boolean;
  has_voice: boolean;
}

export type MemoryType =
  | "story"
  | "fact"
  | "trait"
  | "quote"
  | "value"
  | "routine"
  | "preference"
  | "physical_detail"
  | "advice"
  | "regret"
  | "timeline_event";

export interface Memory {
  id: string;
  type: MemoryType;
  raw_text: string;
}

export interface Person {
  id: string;
  name: string;
  relation_to_persona: string;
  relation_to_user: string;
  notes: string;
}

export interface VoiceSample {
  id: string;
  duration_seconds: number | null;
}

export interface TurnResult {
  transcript: string;
  reply_text: string;
  turn_id: string;
  has_audio: boolean;
  audio_error: string | null;
}

export interface SessionSummary {
  id: string;
  started_at: string;
  turn_count: number;
  last_message: string | null;
}

export interface TurnDetail {
  id: string;
  role: "user" | "assistant";
  text: string;
  has_audio: boolean;
  created_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  is_admin: boolean;
  is_approved: boolean;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_URL}${path}`, { ...init, credentials: "include" });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function signup(email: string, password: string): Promise<{ message: string }> {
  const res = await authFetch("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return asJson(res);
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await authFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return asJson(res);
}

export async function logout(): Promise<void> {
  await authFetch("/auth/logout", { method: "POST" });
}

export async function me(): Promise<AuthUser | null> {
  const res = await authFetch("/auth/me");
  if (res.status === 401) return null;
  return asJson(res);
}

export async function listPendingUsers(): Promise<AuthUser[]> {
  const res = await authFetch("/auth/pending-users");
  return asJson(res);
}

export async function approveUser(userId: string): Promise<AuthUser> {
  const res = await authFetch(`/auth/approve/${userId}`, { method: "POST" });
  return asJson(res);
}

export { ApiError };

// ---------------------------------------------------------------------------
// Personas / memories / voice / sessions
// ---------------------------------------------------------------------------

export async function createPersona(input: {
  name: string;
  relationship_to_user: string;
  gender?: Gender | null;
  user_relationship?: string;
  user_gender?: Gender | null;
  personality_notes: Record<string, string>;
  language: PersonaLanguage;
}): Promise<Persona> {
  const res = await authFetch("/personas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Persona>(res);
}

export async function listPersonas(): Promise<Persona[]> {
  const res = await authFetch("/personas");
  return asJson<Persona[]>(res);
}

export async function getPersona(personaId: string): Promise<Persona> {
  const res = await authFetch(`/personas/${personaId}`);
  return asJson<Persona>(res);
}

export async function deletePersona(personaId: string): Promise<void> {
  const res = await authFetch(`/personas/${personaId}`, { method: "DELETE" });
  if (!res.ok) throw new ApiError(res.status, "Failed to delete persona");
}

export async function updatePersona(
  personaId: string,
  input: Partial<{
    name: string;
    relationship_to_user: string;
    gender: Gender | null;
    user_relationship: string;
    user_gender: Gender | null;
    personality_notes: Record<string, string>;
    language: PersonaLanguage;
    voice_provider: VoiceProvider;
  }>
): Promise<Persona> {
  const res = await authFetch(`/personas/${personaId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Persona>(res);
}

export async function uploadPersonaPhoto(personaId: string, file: File): Promise<Persona> {
  const form = new FormData();
  form.append("file", file);
  const res = await authFetch(`/personas/${personaId}/photo`, {
    method: "POST",
    body: form,
  });
  return asJson<Persona>(res);
}

export function personaPhotoUrl(personaId: string): string {
  return `${API_URL}/personas/${personaId}/photo`;
}

export async function addMemory(
  personaId: string,
  input: { type: Memory["type"]; raw_text: string }
): Promise<Memory> {
  const res = await authFetch(`/personas/${personaId}/memories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Memory>(res);
}

export async function listMemories(personaId: string): Promise<Memory[]> {
  const res = await authFetch(`/personas/${personaId}/memories`);
  return asJson<Memory[]>(res);
}

export async function updateMemory(
  personaId: string,
  memoryId: string,
  input: Partial<{ type: Memory["type"]; raw_text: string }>
): Promise<Memory> {
  const res = await authFetch(`/personas/${personaId}/memories/${memoryId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Memory>(res);
}

export async function deleteMemory(personaId: string, memoryId: string): Promise<void> {
  const res = await authFetch(`/personas/${personaId}/memories/${memoryId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to delete memory");
}

export async function addPerson(
  personaId: string,
  input: { name: string; relation_to_persona: string; relation_to_user: string; notes: string }
): Promise<Person> {
  const res = await authFetch(`/personas/${personaId}/people`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Person>(res);
}

export async function listPeople(personaId: string): Promise<Person[]> {
  const res = await authFetch(`/personas/${personaId}/people`);
  return asJson<Person[]>(res);
}

export async function updatePerson(
  personaId: string,
  personId: string,
  input: Partial<{ name: string; relation_to_persona: string; relation_to_user: string; notes: string }>
): Promise<Person> {
  const res = await authFetch(`/personas/${personaId}/people/${personId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return asJson<Person>(res);
}

export async function deletePerson(personaId: string, personId: string): Promise<void> {
  const res = await authFetch(`/personas/${personaId}/people/${personId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to delete person");
}

export async function uploadVoiceSample(personaId: string, file: File): Promise<VoiceSample> {
  const form = new FormData();
  form.append("file", file);
  const res = await authFetch(`/personas/${personaId}/voice-samples`, {
    method: "POST",
    body: form,
  });
  return asJson<VoiceSample>(res);
}

export async function listVoiceSamples(personaId: string): Promise<VoiceSample[]> {
  const res = await authFetch(`/personas/${personaId}/voice-samples`);
  return asJson<VoiceSample[]>(res);
}

export function voiceSampleAudioUrl(personaId: string, sampleId: string): string {
  return `${API_URL}/personas/${personaId}/voice-samples/${sampleId}/audio`;
}

export async function deleteVoiceSample(personaId: string, sampleId: string): Promise<void> {
  const res = await authFetch(`/personas/${personaId}/voice-samples/${sampleId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to delete voice sample");
}

export async function cloneVoice(personaId: string): Promise<{ provider_voice_id: string }> {
  const res = await authFetch(`/personas/${personaId}/voice-samples/clone`, {
    method: "POST",
  });
  return asJson<{ provider_voice_id: string }>(res);
}

export async function createSession(personaId: string): Promise<{ id: string; persona_id: string }> {
  const res = await authFetch(`/personas/${personaId}/sessions`, { method: "POST" });
  return asJson<{ id: string; persona_id: string }>(res);
}

export async function sendTurn(sessionId: string, audioBlob: Blob): Promise<TurnResult> {
  const form = new FormData();
  form.append("audio", audioBlob, "turn.webm");
  const res = await authFetch(`/sessions/${sessionId}/turns`, {
    method: "POST",
    body: form,
  });
  return asJson<TurnResult>(res);
}

export async function sendTextTurn(sessionId: string, text: string): Promise<TurnResult> {
  const res = await authFetch(`/sessions/${sessionId}/turns/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return asJson<TurnResult>(res);
}

export function turnAudioUrl(sessionId: string, turnId: string): string {
  return `${API_URL}/sessions/${sessionId}/turns/${turnId}/audio`;
}

export async function listSessions(personaId: string): Promise<SessionSummary[]> {
  const res = await authFetch(`/personas/${personaId}/sessions`);
  return asJson<SessionSummary[]>(res);
}

export async function listSessionTurns(sessionId: string): Promise<TurnDetail[]> {
  const res = await authFetch(`/sessions/${sessionId}/turns`);
  return asJson<TurnDetail[]>(res);
}
