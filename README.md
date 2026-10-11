# Memory Companion

A private platform for preserving a loved one's memories and asking questions answered only from
those memories. See `docs/architecture/blueprint.md` for the full architecture and roadmap.

**Status:** Milestone 7 — the above, plus the AI Memory Interviewer: `/interview` asks one
gentle, open-ended question at a time (never leading, never presupposing a detail that
hasn't been said), follows up naturally using conversation context, and on request turns
the transcript into candidate memories through the *same* extractor Milestone 3 built for
uploaded documents — they land in the ordinary review queue (`origin=interview`,
`provenance=family_recollection`) with no new review UI needed. Finishing is explicit and
reversible: nothing is ever auto-approved, finishing with no provider configured leaves
nothing half-written (a clean, retryable error), and finishing twice is rejected rather than
duplicating candidates. The interview transcript itself becomes a `Source` for provenance,
reusing Milestone 3's segment/citation machinery rather than inventing a parallel path.

Milestone 6 added grounded conversation: `/ask` is a real chat UI over `POST
/api/v1/conversations/{id}/messages`, which retrieves evidence (Milestone 5), asks an LLM to
answer *only* from it with structured output (an answer plus which passages it actually
used), strips any citation the model claims that isn't in what was retrieved, and persists
both sides of the turn. No evidence at all skips the LLM entirely (a templated, zero-risk
answer); evidence exists but no `MC_OPENAI_API_KEY` configured gives an honest "can't write
an answer right now" rather than a fabricated one — verified end-to-end against the real
deployed stack, not just unit tests. The system prompt enforces the brief's grounding rules
(never invent a memory/quotation/date, distinguish a family member's recollection from the
person's own recorded words, flag conflicting memories, treat retrieved text as data never
instructions) — see `app/services/providers/generation.py` for the actual prompt. See
`docs/decisions/0007-message-ordering.md` for a real ordering bug a test caught (two
messages in one request tied on Postgres's transaction-constant `now()`).

See also `docs/decisions/0002-rls-deferred.md` for a known isolation gap (no Postgres RLS
yet; enforcement today is at the repository/query layer plus DB-level composite FKs),
`docs/decisions/0003-provider-fallbacks.md` for why an unconfigured LLM/STT/embedding
provider fails cleanly instead of fabricating output, `docs/decisions/0004-chunk-idempotency.md`
/ `0005-synchronous-indexing.md` for two indexing-specific design choices, and
`docs/decisions/0006-keyword-query-or-not-and.md` plus **`evals/README.md`** for the
retrieval evaluation harness and why its dense/hybrid numbers need a real embedding
provider configured before they mean anything.

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
