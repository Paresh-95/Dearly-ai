# Dearly

Dearly is a memory companion. Someone who is gone (or far away) lives on as a
**persona**: the app is grounded in memories you write about them, can speak in
a cloned version of their voice, and answers only from what you have told it.

Each persona has:

- **Memories** — stories, facts, traits, quotes, routines and other
  details. These are chunked and embedded into pgvector, and retrieved per
  turn. They are the only source of facts the persona is allowed to use.
- **People** — relatives and friends connected to the persona. When someone
  is named in your message, their relationship details are added to the
  context.
- **Voice** — uploaded voice samples are cloned into a voice ID, which is then
  used for spoken replies. Fish Audio and Sarvam are supported, and Sarvam is
  used for Marathi.
- **Conversations** — text chat or push-to-talk calls, with saved history per
  session.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the design notes,
[HOW_TO_RUN.md](./HOW_TO_RUN.md) for a Docker walkthrough, and
[GETTING_API_KEYS.md](./GETTING_API_KEYS.md) for API key setup.

## Features

**Personas**
- Create, edit, and delete personas, with name, relationship, gender, and
  language (English or Marathi).
- Upload a profile photo.
- Set the persona's tone, quirks, and speech patterns (`personality_notes`).

**Memories**
- Add memories in 11 types: story, fact, trait, quote, value, routine,
  preference, physical detail, advice, regret, and timeline event.
- Long stories are split into overlapping chunks. Short entries stay whole.
- Edit and delete memories. Chunks are re-embedded on every change.

**People**
- Record related people with their relation to the persona and to you, plus
  notes. There is a list view and a graph view.

**Voice**
- Upload voice samples (MP3, WAV, or M4A, up to 25 MB each) and delete them.
- Clone a voice from the uploaded samples. Fish Audio and Sarvam are the
  providers, selectable per persona.
- Replies are spoken in the cloned voice with an emotional delivery cue
  (warm, concerned, joyful, and so on) taken from the reply.

**Conversation**
- Text chat, or push-to-talk: record, send, and hear the reply.
- Speech-to-text uses Deepgram. Marathi uses its nova-3 model.
- The persona answers from retrieved memories, with a short-term history of
  the last 10 turns.
- The persona can search the web (DuckDuckGo, no API key) when a question
  needs outside information.
- Each stored reply records which memory chunks it was grounded on.
- Saved chat history can be reviewed per session.

**Safety**
- Messages that look like a crisis trigger a dedicated, narrow reply. It
  includes a verified helpline (KIRAN, India), and the model cannot replace it.
- Replies that name phone numbers or hotlines on their own are swapped for
  the verified text.

**Accounts and admin**
- Sign up, then an admin approves the account before it can log in.
- Login uses an HTTP-only JWT cookie.
- The admin account is created from `.env` on startup. The admin panel is at
  `/admin`, where pending users can be approved.
- Login and signup are rate-limited, and so is sending text turns.

## Architecture at a glance

```
Browser (React + Vite)
  │  REST / multipart audio, cookie auth
  ▼
FastAPI backend  ── app/api/*        routes: auth, personas, memories,
  │                                  people, voice samples, sessions
  ├── orchestrator/conversation.py   one turn: history → crisis check →
  │                                  retrieval → LLM → TTS → save
  ├── rag/                           chunking, embeddings, retrieval
  ├── llm/                           prompt builder and chat client
  ├── voice/providers/               Deepgram (STT), Fish Audio, Sarvam (TTS + cloning)
  ├── tools/web_search.py            DuckDuckGo search
  └── storage/object_storage.py      S3-compatible storage (MinIO locally)
  │
  ├── PostgreSQL 16 + pgvector       relational data and memory embeddings
  └── MinIO (private bucket)         voice samples, reply audio, photos
```

**Data model:** `User`, `Persona`, `Person`, `Memory`, `MemoryChunk`
(with a pgvector embedding), `VoiceSample`, `ConversationSession`, and
`ConversationTurn`.

**Retrieval:** a per-persona cosine-distance search over `memory_chunks`,
returning the top 6 chunks. The persona ID is a hard filter, so one persona
never sees another persona's memories. Mentions of people are matched by name.

**Turn flow:** the audio is transcribed (or text is taken directly). The
crisis check runs first. For normal turns, memories and mentioned people are
retrieved, a system prompt is built from the persona's style and the retrieved
memories, and the LLM replies. Then the reply is checked for invented
resources, cleaned for speech, synthesized with the persona's voice, and both
turns are saved. If synthesis fails, the text reply is still returned.

**Stack:** Python 3.12, FastAPI, SQLAlchemy (async), asyncpg, pgvector,
Pydantic, and boto3 for MinIO. Frontend: React 18, React Router, Vite, and
TypeScript.

**Providers:**

| Purpose | Provider | Default model |
|---|---|---|
| Chat (LLM) | Groq (OpenAI-compatible) | `openai/gpt-oss-120b` |
| Embeddings | OpenRouter | `nvidia/nemotron-3-embed-1b:free` |
| Speech synthesis | OpenRouter | `fish-audio/s2.1-pro-free:free` |
| Voice cloning | Fish Audio (direct) | — |
| Voice cloning and speech (Marathi) | Sarvam | `SARVAM_API_KEY` |
| Speech-to-text | Deepgram | — |

## Running with Docker (recommended)

1. Install Docker Desktop and get the API keys listed in
   [GETTING_API_KEYS.md](./GETTING_API_KEYS.md).
2. Copy the example env file and fill it in:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Set `JWT_SECRET` (generate one with `python -c "import secrets; print(secrets.token_hex(32))"`),
   `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.
3. From the project root:
   ```bash
   docker compose up --build
   ```
4. Open http://localhost:5173. Log in as the admin, approve new accounts in
   `/admin`, and create your first persona.

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API (`/docs` for Swagger) | http://localhost:8001 |
| MinIO console | http://localhost:9001 (`minioadmin` / `minioadmin123`) |
| PostgreSQL | localhost:5432 (`postgres` / `postgres`, database `rag_grief`) |

## Running locally without Docker

You need Python 3.12, Node.js, and a Postgres instance with pgvector, plus
MinIO if you want voice storage. You can start just the infrastructure with
`docker compose up db minio`.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in the values
uvicorn app.main:app --reload --port 8001
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_URL=http://localhost:8001
npm run dev
```

The backend creates the `vector` extension, the tables, and the storage
bucket on startup. The schema is managed with `create_all`, not migrations.

## Configuration

All settings are read from `backend/.env` (see `backend/.env.example`).

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (asyncpg) |
| `OPENROUTER_API_KEY`, `EMBEDDING_MODEL`, `TTS_MODEL` | Embeddings and speech synthesis |
| `GROQ_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Chat model |
| `FISH_AUDIO_API_KEY` | Voice cloning and Fish Audio synthesis |
| `SARVAM_API_KEY` | Sarvam voices (optional) |
| `DEEPGRAM_API_KEY` | Speech-to-text |
| `MINIO_*` | Object storage endpoint, credentials, and bucket |
| `JWT_SECRET`, `JWT_EXPIRES_MINUTES`, `AUTH_COOKIE_SECURE` | Login sessions |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | The admin account, synced on each startup |
| `FRONTEND_ORIGINS` | CORS allowlist |

## Project layout

```
RAG-Grief/
├── docker-compose.yml        db (pgvector), minio, backend, frontend
├── ARCHITECTURE.md
├── HOW_TO_RUN.md
├── GETTING_API_KEYS.md
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py           FastAPI app, CORS, routers, startup
│       ├── api/              auth, personas, memories, people,
│       │                     voice_samples, sessions
│       ├── core/             config, security, deps, rate limiting, safety
│       ├── db/               models, session, admin seed
│       ├── rag/              chunking, embeddings, retriever
│       ├── llm/              prompt builder, LLM client
│       ├── orchestrator/     conversation turn pipeline
│       ├── voice/            provider interface, text cleanup,
│       │                     providers/ (deepgram, fish_audio, sarvam)
│       ├── tools/            web search
│       └── storage/          S3/MinIO object storage
└── frontend/
    ├── Dockerfile, nginx.conf
    └── src/
        ├── App.tsx           routes and layout
        ├── api.ts            backend client
        ├── components/       persona, memory, people, voice, call, and
        │                     history pages; admin panel; auth screen
        └── utils/
```

## Notes

- Voice samples, reply audio, and photos are stored in a private MinIO bucket.
  They are served only through authenticated backend endpoints.
- Every query for memories, people, and sessions is scoped to the persona
  and the logged-in user.
- Rate limits are in-memory and per process. They reset on restart and are
  not shared across workers.
- There are no automated tests in this repository yet.
