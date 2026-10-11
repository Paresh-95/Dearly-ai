# ADR 0003 — Unconfigured providers fail the job, never fabricate output

**Status:** accepted (Milestone 3)

Milestone 3 introduces the first two calls to external providers: speech-to-text (audio and
video transcription) and an LLM call that turns extracted text into candidate memories for
review. Neither has credentials configured by default — this is a self-hosted app, and the
person running it supplies their own API key.

**Decision:** every provider is behind a small interface (`SpeechTranscriber`,
`MemoryCandidateExtractor`) with:
1. A real implementation (`OpenAISpeechTranscriber`, `OpenAICandidateExtractor`) that calls an
   OpenAI-compatible endpoint, configurable via `MC_OPENAI_*` so any compatible provider can
   be used, not only OpenAI itself.
2. A factory (`get_speech_transcriber`, `get_candidate_extractor`) that raises
   `ProviderNotConfigured` immediately if `MC_OPENAI_API_KEY` is unset — never returns a
   provider that would silently do nothing or return empty/fake output.
3. A `Fake...` test double, used only by tests that pass it to the worker explicitly
   (`app/workers/ingestion_worker.py:process_one`'s `get_transcriber`/`get_extractor`
   parameters). Nothing in the default configuration path can select a fake provider by
   accident.

When `ProviderNotConfigured` reaches the worker, the ingestion job fails with that exact,
user-facing message (e.g. "No speech-to-text provider is configured…"), following the normal
retry/failure path (`app.repositories.ingestion_jobs.mark_failed`). This is deliberately
**not** a special case: it is just another expected failure, visible in the job's `error`
field, and — critically — it happens *after* extraction's own output (text segments) is
already committed. Uploading a document without an LLM key configured still extracts and
stores its text; only the "suggest memories from this" step is what's blocked, and the error
says so.

**Why not silently skip the step instead of failing the job?** A job marked `succeeded` with
no candidates produced looks, from the review queue, identical to "this document genuinely
had nothing memory-worthy in it" — which is a real, valid outcome. Failing loudly instead
means the two cases stay distinguishable, and the person running the app gets an accurate
signal that adding a provider key would unlock something, rather than a quiet no-op.

**Image OCR is the one deliberate exception**: a missing OCR engine never fails the job (see
`app/services/extraction/image.py`). A plain photograph having no text in it is the normal
case, not a missing-configuration problem, so there is nothing to signal as a failure.
