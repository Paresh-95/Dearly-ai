# Memory Companion

A private platform for preserving a loved one's memories and asking questions answered only from
those memories. See `docs/architecture/blueprint.md` for the full architecture and roadmap.

**Status:** Milestone 5 — the above, plus retrieval: `POST /api/v1/retrieval/search` runs
dense (pgvector cosine) and/or keyword (Postgres full-text) search over a profile's approved,
indexed memories, fuses both with Reciprocal Rank Fusion in hybrid mode, reranks with a
transparent lexical-overlap default, and supports category/date/people filters. No chat or
answer generation yet — this milestone stops at ranked evidence, which is as far as the
brief's roadmap puts it (see `docs/architecture/blueprint.md`). An evaluation harness
(`evals/`) compares dense/keyword/hybrid on a small synthetic fixture dataset; running it is
what caught and fixed a real bug (`docs/decisions/0006-keyword-query-or-not-and.md`) —
**read `evals/README.md` before trusting any number it prints**, since dense/hybrid results
are only meaningful once `MC_OPENAI_API_KEY` is actually set. See also
`docs/decisions/0002-rls-deferred.md` for a known isolation gap (no Postgres RLS yet;
enforcement today is at the repository/query layer plus DB-level composite FKs),
`docs/decisions/0003-provider-fallbacks.md` for why an unconfigured LLM/STT/embedding
provider fails cleanly instead of fabricating output, and
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

Retrieval evaluation (needs a running backend — see `evals/README.md`):

```bash
docker compose up -d db backend
cd backend && uv run python ../evals/run_retrieval_eval.py
```
