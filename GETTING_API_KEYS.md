# Getting Your API Keys

This app needs a handful of API keys from outside services to work — for
AI replies, voice cloning, and speech-to-text. All of the required ones
have a free tier, so this won't cost anything to set up and try.

Once you have each key, paste it into `backend/.env` (after copying it
from `backend/.env.example` — see **HOW_TO_RUN.md**).

---

## 1. OpenRouter (required) — `OPENROUTER_API_KEY`

Used for: understanding/remembering what's been said (embeddings), and
part of the voice reply synthesis.

1. Go to https://openrouter.ai and sign up (free).
2. Go to https://openrouter.ai/keys
3. Click **Create Key**, give it any name.
4. Copy the key (starts with `sk-or-v1-...`) into `OPENROUTER_API_KEY` in
   `backend/.env`.

No payment details needed for the free models this app uses.

---

## 2. Groq (required) — `GROQ_API_KEY`

Used for: generating the AI's actual replies (the chat itself).

1. Go to https://console.groq.com and sign up (free).
2. Go to https://console.groq.com/keys
3. Click **Create API Key**, give it any name.
4. Copy the key (starts with `gsk_...`) into `GROQ_API_KEY` in
   `backend/.env`.

Groq's free tier is generous and fast — no payment details needed.

---

## 3. Fish Audio (required) — `FISH_AUDIO_API_KEY`

Used for: cloning a voice from uploaded audio samples.

1. Go to https://fish.audio and sign up (free).
2. Go to https://fish.audio/app/api-keys/
3. Click to generate a new API key.
4. Copy the key into `FISH_AUDIO_API_KEY` in `backend/.env`.

---

## 4. Deepgram (required) — `DEEPGRAM_API_KEY`

Used for: turning spoken audio (when someone talks instead of types) into
text.

1. Go to https://deepgram.com and sign up (free).
2. Once logged in, go to the **API Keys** section of your Deepgram
   dashboard (console.deepgram.com → API Keys).
3. Create a new key.
4. Copy it into `DEEPGRAM_API_KEY` in `backend/.env`.

Deepgram's free tier includes a meaningful amount of free credit — no
payment details needed to start.

---

## 5. Sarvam AI (optional) — `SARVAM_API_KEY`

Used for: an alternative voice provider, specifically better suited to
Indian languages (e.g. Marathi). Only needed if you want to use Sarvam
instead of (or alongside) Fish Audio.

1. Go to https://sarvam.ai and sign up.
2. Find the API key section in your Sarvam dashboard.
3. Copy the key into `SARVAM_API_KEY` in `backend/.env`. If you don't
   have one, just leave this line out — the app works fine without it,
   using Fish Audio instead.

---

## 6. Your own secret values (no signup needed)

These aren't from an outside service — you generate them yourself.

### `JWT_SECRET`

This secures user login sessions. Generate a random one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

(If you don't have Python installed outside Docker, you can instead open
a terminal *inside* the backend container after first start:
`docker compose exec backend python -c "import secrets; print(secrets.token_hex(32))"`.)

Paste the output into `JWT_SECRET` in `backend/.env`. Never reuse the
placeholder value, and never share this value or commit it anywhere
public.

### `ADMIN_EMAIL` / `ADMIN_PASSWORD`

Pick any email address and a strong password — this becomes the one
admin login for the app (used to approve new users and access `/admin`).
It doesn't need to be a real, working email address; it's just a login
name.

---

## What you do *not* need to touch

- **`MINIO_*`** settings — these are for local file storage (voice
  samples, reply audio) and already match `docker-compose.yml`'s built-in
  MinIO service. Leave them as-is unless you know you need to change them.
- **`DATABASE_URL`** — already points at the database that
  `docker-compose.yml` sets up for you.
- **`FRONTEND_ORIGINS`** — already set correctly for the default setup.

---

## Summary checklist

- [ ] OpenRouter key
- [ ] Groq key
- [ ] Fish Audio key
- [ ] Deepgram key
- [ ] Sarvam key (optional)
- [ ] Generated `JWT_SECRET`
- [ ] Chosen `ADMIN_EMAIL` / `ADMIN_PASSWORD`
