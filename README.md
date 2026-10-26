# AI Memorial Persona — MVP

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the design. This is a push-to-talk
voice-conversation MVP: upload memories + a few voice clips of a loved one,
clone their voice, then talk to an AI persona grounded in those memories.

## 1. Start Postgres (pgvector) and MinIO

```bash
docker compose up -d
```

This also starts MinIO (S3-compatible object storage) for voice samples and
generated reply audio — console at http://localhost:9001 (login
`minioadmin` / `minioadmin123`, see docker-compose.yml). The app creates its
bucket automatically on startup.

> The backend runs on port **8001**, not the more conventional 8000 — on
> Windows, Docker Desktop's own backend process (`com.docker.backend.exe`)
> binds port 8000 for itself and reclaims it on every restart, so this
> project avoids the conflict rather than fight it each time Docker starts.

## 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # then fill in your real API keys
uvicorn app.main:app --reload --port 8001
```

You need API keys for:
- `OPENROUTER_API_KEY` — embeddings (`nvidia/nemotron-3-embed-1b:free`) and
  TTS synthesis (`fish-audio/s2.1-pro-free:free` — the `:free` suffix is
  required) — get one at https://openrouter.ai/keys
- `GROQ_API_KEY` — LLM chat completion, via Groq's OpenAI-compatible endpoint
  (default model `openai/gpt-oss-120b`, fast + generous free tier)
- `FISH_AUDIO_API_KEY` — voice **cloning** specifically. OpenRouter only
  exposes Fish Audio's synthesis endpoint, not cloning, so cloning a voice
  (getting a voice id from uploaded samples) goes directly to Fish Audio's
  own API — get a free key at https://fish.audio/app/api-keys/. Synthesis
  afterwards reuses `OPENROUTER_API_KEY`.
- `DEEPGRAM_API_KEY` — speech-to-text

All of these have free tiers as of writing (see architecture doc discussion) —
the MVP currently uses no paid OpenAI/ElevenLabs API at all.

## 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5173.

## 4. Using it

1. Create a persona (name, relationship, tone/quirks notes).
2. Add a handful of memories (stories, facts, traits, quotes) — these are what
   the AI is allowed to talk about.
3. Upload 1+ short voice clips, then click "Clone voice from uploaded samples".
4. Go to the Call tab, click to record, speak, click again to send, and listen
   to the reply in the cloned voice.

## Notes on this MVP

- No auth, no multi-tenancy, no automated tests, no production logging — by
  design, see ARCHITECTURE.md §8–9. Single local user, `.env`-based keys.
- Push-to-talk (record → send → reply), not a continuous streaming call. A
  real-time WebSocket/WebRTC version is a planned follow-up behind the same
  voice-provider interface.
- Voice samples and generated audio are stored in a private MinIO bucket
  (not public-read) and are never served as static public files — only
  through a server-side lookup endpoint.
