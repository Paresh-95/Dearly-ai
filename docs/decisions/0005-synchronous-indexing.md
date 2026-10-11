# ADR 0005 — Chunking/embedding on approve runs synchronously, not queued

**Status:** accepted (Milestone 4)

Milestone 3 put file ingestion behind an async job queue (`ingestion_jobs` + the worker
process) because that work is genuinely heavy: large files, network transcription, an LLM
call over many extracted segments. Approving a memory is a much smaller unit of work — one
memory, at most a handful of chunks — so Milestone 4 calls the embedding provider directly
inside `POST /memories/{id}/approve`, synchronously, rather than introducing a second queue.

**Why not reuse `ingestion_jobs`?** That table's `source_id` is a required FK to `sources`,
modelling "process this uploaded file." A manually-written memory has no source at all, so
reusing it would mean either making `source_id` nullable (weakening a constraint that is
currently a real safety net) or adding a job-type discriminator and a second nullable target
column — real schema complexity to carry a handful of milliseconds of work asynchronously.

**Trade-off accepted:** the `/approve` request's latency now includes one embedding-provider
HTTP call (when a provider is configured) for however many chunks the memory produced —
typically one call for one chunk. If this becomes a real bottleneck (e.g. bulk-approving many
memories at once), the fix is a dedicated lightweight "reindex" queue, not retrofitting
`ingestion_jobs`. Until then, `POST /memories/{id}/reindex` already gives a manual retry path
for chunks left `pending` because no provider was configured at approval time, so a slow or
flaky provider cannot block approval or lose work.
