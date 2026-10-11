# Memory Companion

A private platform for preserving a loved one's memories and asking questions answered only from
those memories. See `docs/architecture/blueprint.md` for the full architecture and roadmap.

**Status:** Milestone 2 — auth, profiles, consent records, manual memory CRUD with a review
(draft → awaiting review → approved/rejected) workflow, and the frontend onboarding/write/
review/library flow. Ingestion, chunking/embeddings, retrieval and chat are not implemented
yet. See `docs/decisions/0002-rls-deferred.md` for a known isolation gap (no Postgres RLS
yet; enforcement today is at the repository/query layer plus DB-level composite FKs).

## Run locally

```bash
cp .env.example .env
docker compose up -d db            # Postgres 17 + pgvector on :5433
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --port 8100 --reload     # API docs: http://localhost:8100/docs
cd ../frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:8100 npm run dev -- -p 3100
```

Or everything in containers: `docker compose up --build`.

## Tests

```bash
cd backend && uv run pytest        # needs the db container; uses database memory_companion_test
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```
