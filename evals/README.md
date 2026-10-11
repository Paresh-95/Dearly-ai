# Retrieval evaluation

A small, reproducible comparison of dense, keyword and hybrid retrieval, per blueprint §10.
Everything here is synthetic fixture data — not a real person, not real family memories.

## Run it

Needs a running backend (any of these work):

```bash
docker compose up -d db backend
# or, from backend/: uv run uvicorn app.main:app --port 8100

cd backend && uv run python ../evals/run_retrieval_eval.py
```

It registers (or reuses) a fixed eval account, seeds `fixtures/sample_memories.json` as
approved memories under one profile, runs every case in `datasets/retrieval_queries.json`
against all three modes, and writes a timestamped JSON report to `results/` (gitignored —
only the harness and datasets are tracked, not individual runs).

## Read the numbers honestly

**Dense and hybrid results are only meaningful if `MC_OPENAI_API_KEY` is set on the backend.**
Without it, `/retrieval/search` still returns a response in `dense`/`hybrid` mode (per
`docs/decisions/0003-provider-fallbacks.md`, a missing provider is a clean, reported
condition, not an error) — but with zero dense results, every point of apparent "dense"
or "hybrid" performance in that run is actually coming from keyword matching alone, or from
nothing at all. The script detects this (`diagnostics.dense_error` on the response) and
prints a loud warning instead of letting the numbers pass as real. Keyword-only numbers are
real and meaningful either way, since Postgres full-text search needs no external provider.

**Dataset size.** Twelve query cases is enough to catch an obviously broken pipeline and to
illustrate the known cases (direct keyword match, multi-memory, paraphrase, category filter,
no-answer, a prompt-injection-shaped query) — it is not enough to call any percentage here a
real accuracy figure for the product. Treat this as the harness proving it works and as a
regression check, not as a benchmark result to quote.

**Known gaps**, left for a follow-up rather than filled with low-confidence content now:
- No non-English query cases yet, despite the product supporting multiple languages.
- The reranker is the deliberately simple lexical-overlap default (see
  `app/services/retrieval/reranker.py`); this harness is exactly what would be used to decide
  whether a real reranking model is worth adding.
- Latency here is one sequential run on a local/dev machine, not a load test.
