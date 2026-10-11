# ADR 0001 — Modular monolith, Postgres-only data plane

**Status:** accepted (Milestone 1)

- One FastAPI service (+ a worker process from Milestone 3 using the same code). No microservices.
- PostgreSQL holds relational data, pgvector embeddings (HNSW, cosine) and full-text search
  (`tsvector`, `'simple'` config so mixed-language memories are not stemmed incorrectly).
- Job queue is a Postgres table (`ingestion_jobs`), not Redis/Celery.
- Tenant isolation: every profile-scoped row carries `(person_profile_id, user_id)` with a composite
  FK to `person_profiles(id, user_id)`, so the database rejects a row that names another user's
  profile. Repositories also filter by `user_id`; cross-user access returns 404 (no existence leak).
  Postgres RLS is planned for Milestone 2 as defence in depth.
- Embedding dimension (1536) is fixed in migration 0001. Changing model dimension needs a new migration and reindex; the model name is stored per chunk.
- Auth: argon2id passwords; 15-min access JWT held in memory by the SPA; 14-day refresh JWT in an
  httpOnly cookie scoped to `/api/v1/auth`. **Known limitation:** refresh tokens are stateless, so
  logout only clears the cookie; server-side revocation (token version / session table) is a
  follow-up.
- No voice synthesis exists; `voice_synthesis` is reserved as a consent type only.
