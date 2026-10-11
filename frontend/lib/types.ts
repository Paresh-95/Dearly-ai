export interface User {
  id: string;
  email: string;
  display_name: string | null;
}

export interface Profile {
  id: string;
  name: string;
  relationship: string;
  preferred_name: string | null;
  languages: string[];
  biography: string | null;
  personality: string | null;
  favourite_expressions: string[];
  hobbies: string[];
  important_relationships: Record<string, unknown>[];
  birth_date: string | null;
  death_date: string | null;
  created_at: string;
  updated_at: string;
}

export type MemoryStatus = "draft" | "awaiting_review" | "approved" | "rejected";

export interface MemoryPerson {
  id: string;
  name: string;
  relationship: string | null;
}

export interface Memory {
  id: string;
  person_profile_id: string;
  title: string;
  description: string;
  status: MemoryStatus;
  origin: string;
  provenance: string;
  category: string | null;
  date_text: string | null;
  date_start: string | null;
  date_end: string | null;
  location: string | null;
  is_uncertain: boolean;
  uncertainty_note: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
  people: MemoryPerson[];
}

export interface MemoryList {
  items: Memory[];
  next_cursor: string | null;
  total: number;
}

export type ConsentType = "data_processing" | "external_ai_provider" | "voice_synthesis";

export interface Consent {
  id: string;
  consent_type: ConsentType;
  granted: boolean;
  policy_version: string;
  person_profile_id: string | null;
  provider: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

/** Keep in sync with the backend's current privacy-policy text (see docs/architecture). */
export const CONSENT_POLICY_VERSION = "v1";

export const MEMORY_CATEGORIES = [
  "personality",
  "daily_life",
  "family",
  "memorable_events",
  "communication_style",
  "other",
] as const;

export const UPLOAD_KINDS = [
  { value: "text", label: "Text document (.txt)" },
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "Word document (.docx)" },
  { value: "whatsapp", label: "WhatsApp chat export" },
  { value: "image", label: "Photo" },
  { value: "audio", label: "Audio recording" },
  { value: "video", label: "Video" },
] as const;

export type JobState = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface IngestionJob {
  id: string;
  source_id: string;
  person_profile_id: string;
  state: JobState;
  stage: string | null;
  progress: number | null;
  attempts: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface IngestionJobList {
  items: IngestionJob[];
}

export interface Source {
  id: string;
  person_profile_id: string;
  kind: string;
  provenance: string;
  filename: string | null;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface SourceList {
  items: Source[];
}
