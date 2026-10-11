# ADR 0006 — Keyword search ORs query words instead of ANDing them

**Status:** accepted (Milestone 5)

The first implementation of `app/services/retrieval/keyword.py` used
`websearch_to_tsquery`, which combines every word in the query with AND by default. Running
`evals/run_retrieval_eval.py` against it (see `evals/README.md`) measured **zero** recall on
every single query in the fixture dataset, including the ones deliberately written for
direct lexical overlap — not a close call, a complete failure.

The cause: people ask full questions ("What did Mum make for breakfast on Sundays?"), and
`websearch_to_tsquery`'s AND semantics require *every* word — including "what", "did", "for",
"on" — to appear in the matched text. A short memory chunk almost never contains every
function word of the question that was asked about it, so the query matched nothing.

**Decision:** `keyword.search` now tokenises the query itself and ORs the lexemes together
(`to_tsquery('simple', 'word1 | word2 | ...')`), while `ts_rank` still ranks a chunk matching
more of the query's words above one matching fewer — so the ranking still rewards overlap,
it just no longer requires total overlap to return anything at all. Re-running the
evaluation after this change went from 0.0 to 0.75 Recall@5 / 0.6 MRR on the same fixture
set (see the `evals/README.md` caveats on what that number does and doesn't prove — it is
real, since keyword search needs no embedding provider, but twelve queries is a smoke test,
not a benchmark).

**Consequence worth naming:** OR semantics mean keyword search almost always returns *some*
result, even for a query nothing actually answers (see the `no_answer_*` fixture cases — they
still get a top "best effort" match). Recognising that retrieved evidence doesn't actually
support an answer, and saying so, is explicitly Milestone 6's job (grounding/abstention), not
retrieval's — retrieval's contract is "best candidates for this query," never "there is no
answer."
