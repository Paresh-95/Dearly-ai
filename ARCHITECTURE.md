# AI Memorial Persona — Architecture (MVP)

## 0. Goal

A grieving user supplies memories (stories, facts, personality notes, quotes) and a
few voice samples of a deceased/absent loved one. The app lets them have a spoken,
phone-call-like conversation with an AI persona that speaks in that person's cloned
voice and answers **only** using the supplied memories — never invented facts.

This MVP intentionally has **no auth, no multi-tenancy, no production logging,
no rate limiting**. Single user, local/dev deployment, API keys via `.env`.

## 1. Pipeline

```
Browser (record/upload audio)
   -> POST /sessions/{id}/turns  (multipart audio)
   -> STT (transcribe)
   -> RAG retrieval (pgvector, scoped by persona_id)
   -> grounded prompt -> LLM (chat completion)
   -> TTS (cloned voice) -> audio file
   -> response: { transcript, reply_text, reply_audio_url }
```

MVP v1 uses **push-to-talk** (record a clip, send it, get a reply) rather than a
continuously streaming WebSocket call — this is the fastest path to a working,
testable end-to-end loop. Streaming/WebRTC real-time can be layered on later behind
the same `VoicePipelineProvider` interface without changing the RAG/LLM core.

## 2. Storage

- **Postgres + pgvector** — one database for relational data (Persona, Memory,
  VoiceSample, ConversationSession/Turn) and for memory embeddings
  (`memory_chunks.embedding`). Avoids running a second vector-DB service for MVP
  scale (tens-hundreds of memory chunks per persona).
- **MinIO** (S3-compatible, run via docker-compose) holds voice samples and
  generated reply audio in a private bucket — never served directly as static
  files, always read back through a server endpoint. Swap for a managed S3/GCS
  bucket later behind the same `storage/` module without touching callers.

## 3. LLM grounding strategy

- System prompt is built from two separate parts:
  - **Style** — persona's tone/quirks/speech patterns (`Persona.personality_notes`).
  - **Substance** — the retrieved memory chunks for this turn, injected as the
    *only* allowed source of facts/opinions/stories.
- Explicit instruction: if the retrieved memories don't cover the question, the
  model must deflect in-character rather than invent an answer.
- Low temperature (0.4) for conversational-but-controlled output.
- Every assistant turn stores the `retrieved_memory_ids` it was grounded on, for
  auditability.

## 4. Voice provider abstraction

`backend/app/voice/provider_interface.py` defines:
- `transcribe(audio_bytes) -> str`
- `clone_voice(sample_paths: list[str]) -> str` (returns provider voice id)
- `synthesize(text: str, voice_id: str) -> bytes` (audio)

MVP ships one concrete adapter: **ElevenLabs** (TTS + instant voice cloning) and
**Deepgram** (STT), chosen for cheap/free tiers and fast iteration. Both are
swappable — add a new file under `voice/providers/` and flip an env var.

## 5. Backend stack

- **Python + FastAPI**, async throughout.
- REST for CRUD (`/personas`, `/personas/{id}/memories`, `/personas/{id}/voice-samples`).
- REST (not WebSocket yet) for the conversation turn in v1 — multipart audio
  upload in, JSON + audio URL out. Simplest thing that works end-to-end; a
  WebSocket/streaming version is a planned follow-up, not part of this MVP.
- SQLAlchemy (async) + `Base.metadata.create_all` on startup — no Alembic yet
  (MVP: schema stability not required, just rebuild the dev DB when models change).

## 6. Frontend stack

- React + Vite + TypeScript, no router complexity needed (a handful of views
  swapped by local state).
- Screens: Persona setup, Memory input, Voice sample upload, Call (push-to-talk).

## 7. Data model

```
Persona(id, name, relationship_to_user, personality_notes JSON, provider_voice_id, created_at)
Memory(id, persona_id, type[story|fact|trait|quote], raw_text, created_at)
MemoryChunk(id, memory_id, persona_id, chunk_text, embedding vector(1536), created_at)
VoiceSample(id, persona_id, storage_path, duration_seconds, uploaded_at)
ConversationSession(id, persona_id, started_at, ended_at)
ConversationTurn(id, session_id, role[user|assistant], text, retrieved_memory_ids JSON, audio_path, created_at)
```

## 8. Must-not-skip basics (even without auth)

- No secrets hardcoded — everything via `.env` (see `.env.example`), `.gitignore`
  excludes `.env`.
- Voice samples and generated audio live in a private MinIO bucket, served
  only via a server endpoint that checks the row exists — bucket is never
  public, no static mount.
- Every memory/voice-sample query scoped by `persona_id`.
- Uploaded audio validated by content-type + size limit before processing.
- Generic error responses to the client; details only in server logs.
- CORS allowlist (frontend dev origin only), not `*`.

## 9. Deferred post-MVP

Auth/accounts, multi-tenancy, production logging/observability, rate limiting,
payments, content moderation at scale, horizontal scaling, mobile apps,
continuous WebSocket/WebRTC streaming call (replacing push-to-talk), automated
grounding verification.

## 10. Repo layout

```
RAG-Grief/
├── ARCHITECTURE.md
├── docker-compose.yml
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/config.py
│       ├── db/{models.py,session.py}
│       ├── rag/{chunking.py,embeddings.py,retriever.py}
│       ├── llm/{prompt_builder.py,llm_client.py}
│       ├── voice/{provider_interface.py,providers/}
│       ├── orchestrator/conversation.py
│       └── api/{personas.py,memories.py,voice_samples.py,sessions.py}
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/{App.tsx,api.ts,pages/}
```
