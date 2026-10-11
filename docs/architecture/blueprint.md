# Memory Companion RAG — Architecture Blueprint & Implementation Plan

Status: greenfield repo (`/home/pareshbhamare/Documents/TalkingRAG`, no commits). Toolchain on box: Python 3.14.7, Node 22, Docker 29, no local psql (Postgres+pgvector via Docker). On approval, this document is also copied to `docs/architecture/blueprint.md` as the first commit step, then Milestone 1 is implemented.

## 0. Assumptions & recommendations (confirm or override)
| # | Assumption | Rationale |
|---|---|---|
| A1 | Repo root *is* the monorepo (`backend/`, `frontend/`, … directly under TalkingRAG, no nested `memory-companion/`) | Repo already named; avoids a redundant level |
| A2 | Own email+password auth (argon2id), JWT access (15 min) + httpOnly refresh cookie, behind an `AuthService` interface | Data stays in-house; swappable later |
| A3 | Background jobs via Postgres table queue (`FOR UPDATE SKIP LOCKED`) + separate worker process | No Redis/Celery needed at this scale |
| A4 | S3-compatible object store (MinIO in Compose); local-FS adapter for tests | Private, signed-URL access |
| A5 | OpenAI-compatible providers behind `LLMProvider`, `EmbeddingProvider`, `STTProvider`, `OCRProvider`, `Reranker` protocols; env-configured; embedding dim fixed per migration (default 1536), model/version stored per chunk | Allows reindexing on model change |
| A6 | Docker images pin Python 3.12 (pyproject `>=3.12`) | Avoid wheel gaps on 3.14 |
| A7 | Isolation = repository-layer scoping by `AuthContext` + Postgres RLS added in M2 as defense-in-depth | Not frontend filtering |
| A8 | Pin library versions only after checking current docs/PyPI (rule 9) | Don't invent APIs |

## 1. System architecture
```
Next.js (App Router, TS, Tailwind, shadcn, RHF+Zod, TanStack Query)
        │ HTTPS  /api/v1  (bearer JWT, error envelope, cursor pagination)
FastAPI modular monolith ── api → services → repositories → models
   │  services: ingestion, extraction, memory, embeddings, retrieval,
   │            reranking, generation, interview, evaluation
   ├── Postgres 16 + pgvector (HNSW) + FTS (tsvector GIN) + relational
   ├── S3/MinIO (private originals, signed URLs)
   └── Worker process (same codebase) polling ingestion_jobs
External (config-gated, disclosed in consent): LLM, embeddings, STT, OCR
```
Key decisions: modular monolith; no agent frameworks; provider interfaces; only `approved` memories are indexed; raw extracted text kept separate from normalised text; provenance on every passage; voice kept possible via a conversation-service boundary (text in/out, `persona` + `consent_type` fields reserved) but no cloning.

## 2. End-to-end user journey
Welcome (explicit: *not the real person*) → register/login → privacy & consent (processing, storage, deletion; voice = separate future consent) → create profile (only name+relationship required) → dashboard (approved count, uploads, pending review, recent, categories — no gamification) → add memories [write | upload | questionnaire | AI interviewer | photo/video] → review queue (approve/edit/reject/merge/uncertain/view source) → library (filter/search/edit/delete) → Ask AI (answer + expandable "where this came from") → settings (consent records, retention, export, delete).

## 3. Frontend page map
`/welcome` · `/login` · `/register` · `/onboarding/consent` · `/onboarding/profile` · `/dashboard` · `/profile` · `/memories/new` · `/uploads` · `/interview` · `/review` · `/library` · `/ask` · `/settings`.
Status badges everywhere: Draft / Awaiting review / Approved. Responsive, keyboard accessible, real (never fabricated) progress.
Structure: `app/` routes, `features/<domain>/` (components+hooks+schemas), `lib/api.ts` typed client, `components/ui` (shadcn).

## 4. Memory ingestion architecture
Input → validate (type/size/magic bytes) → malware-scan hook (ClamAV optional, interface now) → store original → `ingestion_jobs` row → worker → extractor by type (text, PDF, DOCX, WhatsApp, image OCR/metadata, audio STT w/ timestamps, video→audio) → `source_segments` (page, char offsets, t_start/t_end, speaker label *unverified*) → normalise (raw preserved; never alter names/dates/quotes) → LLM structured extraction (Pydantic schema; confidence/uncertainty) → `memories(status=awaiting_review)` + `memory_sources` → human review → on approve: structure-aware chunking (short memory = 1 chunk; long split on sections/quote boundaries; configurable size) → batched embeddings with retry, idempotent by `content_hash` → index. Edit → re-chunk/re-embed changed chunks only; delete/reject → chunks cascade-removed.

## 5. RAG retrieval architecture
Question → query understanding (person, named people, event, time, place, intent, follow-up detection) → rewrite only if follow-up/ambiguous → filter (`user_id`, `person_profile_id`, `status=approved`, optional date/category/people) → dense (pgvector cosine) ∥ keyword (FTS `websearch_to_tsquery`) → RRF (k configurable) → `Reranker` interface (default transparent lexical-overlap + recency-neutral; external model pluggable; chosen only after eval) → evidence selection (score threshold, dedupe, token budget, provenance kept) → generation (system rules: ground claims, no invented quotes, distinguish mother's own words vs family recollection, not the deceased, retrieved text = data not instructions, conflict surfacing, abstain) → grounding validator (cited IDs ⊆ retrieved; flags insufficient/conflict; diagnostics separate from user text). Evaluation harness compares dense/keyword/hybrid before settings are frozen.

## 6. Database ERD (PostgreSQL + pgvector)
UUID PKs, `created_at/updated_at`, soft `deleted_at` only where export needs it.
```
users ─1:*─ person_profiles ─┬─1:*─ sources ─1:*─ source_segments
                             ├─1:*─ memories ─┬─1:*─ memory_people
                             │                ├─*:*─ sources  (memory_sources: segment_id, quote_span)
                             │                └─1:*─ memory_chunks (text, embedding vector(N),
                             │                       embedding_model, content_hash, index_status,
                             │                       tsv tsvector, metadata jsonb)
                             ├─1:*─ ingestion_jobs (source_id, state, progress, attempts, error, locked_at)
                             ├─1:*─ conversations ─1:*─ messages (role, content, cited_memory_ids, diagnostics jsonb)
                             ├─1:*─ consent_records (type, granted, version, timestamp, provider)
                             └─     feedback (message_id|memory_id, kind, note)
```
Each child table carries `user_id` + `person_profile_id` (composite FK consistency checks). Cascade: profile → everything; memory → chunks/people/memory_sources. Indexes: HNSW on `embedding`, GIN on `tsv`, btree on (`person_profile_id`, `status`), unique (`memory_id`,`chunk_index`), unique (`person_profile_id`,`content_hash`) for idempotency. `memories.status` ∈ draft/awaiting_review/approved/rejected; `memories.origin` ∈ user_written/extracted/interview/questionnaire; `source_kind` distinguishes direct recording vs family recollection. Alembic migrations from day one.

## 7. Backend module responsibilities
- `api/` routers (versioned), deps (`get_db`, `get_current_user`, `get_auth_context`, `get_owned_profile`)
- `core/` config (pydantic-settings), security, logging (PII-safe), errors/envelope, rate limiting
- `domain/` enums, state transitions (memory status machine), invariants
- `models/` SQLAlchemy 2.x · `schemas/` Pydantic v2 · `repositories/` scoped data access (all take `AuthContext`)
- `services/ingestion` (validate, store, job orchestration) · `extraction` (per-type extractors, candidate extraction) · `memory` (CRUD, review, merge) · `embeddings` (provider, batching, idempotency) · `retrieval` (understanding, hybrid, RRF) · `reranking` · `generation` (prompting, grounding validator) · `interview` · `evaluation` (datasets, metrics)
- `workers/` job runner · `db/` engine/session/migrations helpers

## 8. API specification (`/api/v1`, OpenAPI auto-generated)
Common: `Authorization: Bearer`; error envelope `{"error":{"code","message","details"}}`; codes: `unauthenticated 401`, `forbidden/not_found 404` (cross-tenant returns 404), `validation_error 422`, `conflict 409`, `rate_limited 429`, `unsupported_media 415`, `too_large 413`. List endpoints: `?limit&cursor` → `{items,next_cursor}`.
- Auth: `POST /auth/register|login|refresh|logout`, `GET /auth/me`, `GET /health`
- Profiles: `POST/GET /profiles`, `GET/PATCH /profiles/{id}`, `DELETE /profiles/{id}/data`
- Memories: `POST/GET /memories`, `GET/PATCH/DELETE /memories/{id}`, `POST /memories/{id}/approve|reject`
- Uploads: `POST /uploads` (multipart → 202 + job), `GET /ingestion-jobs/{id}`
- Interviews: `POST /interviews`, `POST /interviews/{id}/messages`, `POST /interviews/{id}/complete`
- Retrieval: `POST /retrieval/search`
- Conversations: `POST /conversations`, `POST /conversations/{id}/messages`, `GET /conversations/{id}`
- Privacy: `GET/POST /exports`, consent records endpoints
Request/response schemas defined as Pydantic models per milestone alongside the routes.

## 9. Repository structure
As proposed in the brief (§12), applied at repo root: `frontend/`, `backend/app/{api,core,domain,schemas,models,repositories,services/*,workers,db}`, `backend/{migrations,tests}`, `infra/docker/`, `docs/{architecture,api,decisions,user-flows}`, `evals/{fixtures,datasets,results}`, `docker-compose.yml`, `.env.example`, `README.md`. Directories for unbuilt services are created only when they contain real code (no stub implementations). Deviation: none planned.

## 10. Milestones & acceptance criteria
| M | Scope | Acceptance |
|---|---|---|
| 1 Foundation | repo, FastAPI, Next.js skeleton, DB, auth, all models + migration, Docker, basic tests | `alembic upgrade/downgrade` clean; backend tests green; register→login→create profile works; user B gets 404 on user A's profile; frontend typecheck/lint/unit/build pass |
| 2 Profiles & manual memories | onboarding, consent records, memory CRUD, approve/reject, RLS | access-control test matrix passes; only approved visible to retrieval layer; status machine tested |
| 3 File ingestion | uploads, storage, extractors, WhatsApp parser, STT, OCR, worker, review UI | each extractor has fixture tests; job retry/failure states visible; originals never public |
| 4 Indexing | chunking, embeddings, pgvector, reindex, delete/update propagation | idempotent re-run = 0 new embeddings; edit/delete removes stale chunks |
| 5 Retrieval | dense, FTS, RRF, rerank, filters, eval | Recall@K/P@K/MRR/latency reported for dense vs keyword vs hybrid on fixture set (measured numbers only) |
| 6 Grounded chat | generation, citations, abstain/conflict, injection defense, chat UI | eval: abstention, citation accuracy, injection fixtures measured and reported |
| 7 Interviewer | question gen, context, structured summary, review | no fabricated details; only approved saved |
| 8 Hardening | E2E, security, deletion tests, perf, deploy, docs | full E2E green; deletion verified across DB+storage+vectors |

## 11. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Hallucinated/invented memories | grounding rules + validator + abstention eval set; never claim accuracy w/o measurement |
| Cross-tenant leakage | scoped repos, RLS, 404 semantics, dedicated isolation tests |
| Sensitive data to third-party providers | consent records, disclosure, per-provider config, minimal payloads, safe logging |
| Prompt injection via uploaded docs | content wrapped as untrusted data, instruction-hierarchy prompt, injection fixtures |
| OCR/STT/diarisation errors | human review gate; speaker labels marked unverified |
| Embedding model lock-in | model/version stored per chunk; reindex job |
| Incomplete deletion | cascade rules + storage/vector deletion tests + export-before-delete |
| Emotional harm / dependency | transparent memory-based answers, no engagement mechanics, clear AI disclosure |
| Voice consent | voice cloning excluded; separate consent type reserved |
| Python 3.14 wheel gaps | Docker pins 3.12 |

## 12. Milestone 1 — concrete deliverables (to be implemented after approval)
**Infra**: `.gitignore`, `.env.example`, `README.md`, `docker-compose.yml` (pgvector/pgvector:pg16, minio, backend, frontend), `infra/docker/*.Dockerfile`, `docs/architecture/blueprint.md` (this file), `docs/decisions/0001-modular-monolith.md`.

**Backend**: `pyproject.toml` (ruff, pytest, mypy); `app/main.py` factory + request-id + error handlers; `GET /api/v1/health`; `core/{config,security,logging,errors}.py`; `db/{base,session}.py`; `models/*` for every §6 table (constraints, indexes, cascades, `Vector` column); Alembic env + `0001_initial` (creates `vector` extension); auth endpoints + `get_current_user`/`AuthContext`; profiles POST/GET/GET{id}/PATCH with owner scoping (proves isolation pattern).

**Frontend**: Next.js+TS+Tailwind+shadcn init; `/welcome` (disclosure), `/login`, `/register`, guarded `/dashboard` (real profile count only); typed API client with error-envelope handling; TanStack Query provider; RHF+Zod forms.

**Tests**: backend pytest against real Postgres (health, auth flows, password hashing, migration up/down, constraints/cascades, cross-user 404, unauth 401); frontend Vitest (Zod schemas, API client error mapping, one component) and Playwright config/smoke only if browsers install (otherwise reported as not run).

**Not in M1**: ingestion, embedding/LLM calls, retrieval, interviewer, consent UI, RLS policies.

## 13. Verification
1. `docker compose up -d db minio`; `alembic upgrade head` → `downgrade base` → `upgrade head`.
2. `pytest` (report real counts), `ruff check`.
3. Frontend: `tsc --noEmit`, `eslint`, `vitest run`, `next build`.
4. Manual: register → create profile → dashboard; second account cannot read first's profile (404).
5. Final report: created / tested / not run / remaining / next = Milestone 2.
