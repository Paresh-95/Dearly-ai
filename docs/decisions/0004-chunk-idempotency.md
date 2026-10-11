# ADR 0004 — memory_chunks idempotency is an app-level check, not a DB constraint

**Status:** accepted (Milestone 4)

Migration 0001 added `UNIQUE (person_profile_id, content_hash)` on `memory_chunks`, intended
to satisfy the brief's "do not create duplicate embeddings for unchanged content." Building
the actual reindexing logic in Milestone 4 showed this was the wrong mechanism: the
constraint also rejects two **different** memories that happen to produce identical chunk
text under the same profile (e.g. both quoting the same well-known family saying verbatim).
That is a real, legitimate coincidence, not a retried operation, and should not fail.

**Decision:** migration 0002 drops that unique constraint (keeping a plain, non-unique index
on the same columns for lookups) and `content_hash` is used **only** in application code:
`app/repositories/memory_chunks.py` compares the newly computed hash for a given
`(memory_id, chunk_index)` against the hash already stored there. Unchanged → the existing
embedding is kept and no provider call is made. Changed (or missing) → the chunk is
re-embedded. This is the actual idempotency guarantee the brief asked for, scoped correctly
to "has *this* chunk's content changed since it was last embedded," not "is this text unique
across the whole profile."
