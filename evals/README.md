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

**Dataset size.** Fourteen query cases is enough to catch an obviously broken pipeline and to
illustrate the known cases (direct keyword match, multi-memory, paraphrase, category filter,
no-answer, a prompt-injection-shaped query, Hindi/Marathi) — it is not enough to call any
percentage here a real accuracy figure for the product. Treat this as the harness proving it
works and as a regression check, not as a benchmark result to quote.

**Multi-language.** Two cases (`marathi_direct_overlap`, `hindi_direct_overlap`) are plain
Devanagari questions against Devanagari memories, added after finding and fixing a real bug
this way: the keyword word-extractor only matched `[a-zA-Z0-9]`, so a pure-Hindi or
pure-Marathi query matched nothing at all, unconditionally (see
`docs/decisions/0008-multilingual-tokenization.md`). After the fix, both correctly retrieve
their target memory — recall@5 on this fixture set went from 0.750 to 0.792 once they were
added and passing. The same caveat about dense/hybrid applies equally here: without a real
embedding provider configured, only the keyword-search result for these two is a real
measurement.

**Known gaps**, left for a follow-up rather than filled with low-confidence content now:
- Only two non-English cases, both Devanagari and both a direct keyword match — no
  paraphrase-style or multi-memory Hindi/Marathi case yet, and no other language family.
- The reranker is the deliberately simple lexical-overlap default (see
  `app/services/retrieval/reranker.py`); this harness is exactly what would be used to decide
  whether a real reranking model is worth adding.
- Latency here is one sequential run on a local/dev machine, not a load test.
