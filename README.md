# Memory Companion

A private platform for preserving a loved one's memories and asking questions answered only from
those memories. See `docs/architecture/blueprint.md` for the full architecture and roadmap.

**Status:** Milestone 4 — the above, plus memory indexing: approving a memory chunks it
(memory-aware: short memories stay intact, long ones split on sentence boundaries) and
embeds each chunk via a configurable embedding provider. Editing or rejecting an approved
memory clears its chunks immediately (re-approving re-chunks from the current content); an
unconfigured embedding provider leaves chunks `pending` rather than blocking approval, and
`POST /memories/{id}/reindex` retries them once one is configured. Retrieval (actually
*searching* those embeddings) and chat are not implemented yet — see
`docs/architecture/blueprint.md` for the roadmap. See `docs/decisions/0002-rls-deferred.md`
for a known isolation gap (no Postgres RLS yet; enforcement today is at the repository/query
layer plus DB-level composite FKs), `docs/decisions/0003-provider-fallbacks.md` for why an
unconfigured LLM/STT/embedding provider fails cleanly instead of fabricating output, and
`docs/decisions/0004-chunk-idempotency.md` / `0005-synchronous-indexing.md` for two
indexing-specific design choices.

## Run locally

```bash
cp .env.example .env
docker compose up -d db minio      # Postgres 17 + pgvector on :5433, MinIO (S3) on :9100
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --port 8100 --reload     # API docs: http://localhost:8100/docs
uv run python -m app.workers.ingestion_worker        # in another shell, for uploads to be processed
cd ../frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:8100 npm run dev -- -p 3100
```

Or everything in containers: `docker compose up --build` (brings up `backend`, `worker` and
`frontend` alongside `db`/`minio`). Set `MC_OPENAI_API_KEY` in `.env` to enable real speech-to-
text and LLM-based memory suggestions from uploads; without it, uploads still extract and
store text, but candidate-memory generation fails that job step with a clear message (see
`docs/decisions/0003-provider-fallbacks.md`). Local dev defaults to on-disk storage
(`MC_STORAGE_BACKEND=local`); the Docker Compose services use the `s3`/MinIO backend instead.

## Tests

```bash
cd backend && uv run pytest        # needs the db container; uses database memory_companion_test
                                    # (add MC_RUN_S3_TESTS=1, with `docker compose up -d minio`,
                                    # to also exercise the real S3-backed storage adapter)
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```
