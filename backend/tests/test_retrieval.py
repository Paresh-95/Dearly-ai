from uuid import uuid4

from app.services.retrieval.base import RetrievedChunk
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import LexicalOverlapReranker
from tests.test_memories import make_memory, profile_id
from tests.test_memory_indexing import fake_provider, patch_embeddings


def chunk(score: float = 0.0, text: str = "x") -> RetrievedChunk:
    return RetrievedChunk(chunk_id=uuid4(), memory_id=uuid4(), text=text, metadata={}, score=score)


def patch_all_embeddings(monkeypatch):
    """`patch_embeddings` only covers the indexing path (what approve() uses); dense search
    resolves its own embedding provider through a separate import in
    app.services.retrieval.pipeline, which needs patching too."""
    patch_embeddings(monkeypatch)
    monkeypatch.setattr("app.services.retrieval.pipeline.get_embedding_provider", fake_provider)


class TestReciprocalRankFusion:
    def test_an_item_ranked_well_by_both_methods_wins(self):
        a, b = chunk(), chunk()
        fused = reciprocal_rank_fusion([[a, b], [a, b]])
        assert [c for c, _ in fused] == [a, b]

    def test_agreement_across_methods_beats_a_single_top_rank(self):
        a, c = chunk(), chunk()
        # a is #1 in method one only (absent from method two).
        # c is #2 in method one but also #1 in method two -- agreed upon by both.
        fused = reciprocal_rank_fusion([[a, c], [c]])
        ordered = [x for x, _ in fused]
        assert ordered[0] is c

    def test_items_absent_from_a_list_are_not_penalised_twice(self):
        a, b, c = chunk(), chunk(), chunk()
        fused = reciprocal_rank_fusion([[a, b], [c]])
        assert {x.chunk_id for x, _ in fused} == {a.chunk_id, b.chunk_id, c.chunk_id}


class TestLexicalOverlapReranker:
    def test_more_overlapping_tokens_ranks_higher(self):
        low = chunk(text="completely unrelated sentence about cars")
        high = chunk(text="Mum always made poha every Sunday morning")
        ranked = LexicalOverlapReranker().rerank("poha Sunday morning", [low, high])
        assert ranked[0][0] is high
        assert ranked[0][1] > ranked[1][1]

    def test_empty_query_scores_everything_zero_and_keeps_order(self):
        a, b = chunk(text="first"), chunk(text="second")
        ranked = LexicalOverlapReranker().rerank("", [a, b])
        assert [c for c, _ in ranked] == [a, b]
        assert all(score == 0.0 for _, score in ranked)


class TestPipelineIntegration:
    def _approved_memory(self, client, headers, pid, **kwargs):
        m = make_memory(client, headers, pid, status="awaiting_review", **kwargs)
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=headers)
        return m

    def test_hybrid_search_finds_an_approved_memory_by_keyword(self, client, alice, monkeypatch):
        patch_all_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="Sunday breakfast",
            description="Mum always made poha every Sunday morning.",
        )

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "poha Sunday"},
            headers=alice,
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        assert "poha" in body["items"][0]["text"].lower()
        assert body["diagnostics"]["mode_used"] == "hybrid"
        assert body["diagnostics"]["keyword_count"] >= 1
        assert body["diagnostics"]["took_ms"] >= 0

    def test_keyword_search_finds_a_marathi_memory_by_a_marathi_query(self, client, alice):
        """Regression test: the word-extractor used to build the OR-tsquery only matched
        [a-zA-Z0-9], so it matched nothing at all in Devanagari text -- a Hindi/Marathi
        query returned zero results unconditionally, regardless of what was approved."""
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="आईच्या आठवणी",
            description="आई नेहमी रविवारी पोहे बनवत असे. ती सकाळी आठ वाजता सर्वांना उठवत असे.",
        )

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "रविवारी पोहे कोण बनवत असे?", "mode": "keyword"},
            headers=alice,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_dense_mode_finds_an_exact_text_match(self, client, alice, monkeypatch):
        # The fake embedding provider has no real semantic signal, so this only proves the
        # dense-search wiring (cosine distance, filtering, ordering) is correct -- an exact
        # text match always embeds identically to itself, giving distance 0 regardless of
        # whether the vectors mean anything semantically. See evals/README.md.
        patch_all_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        m = self._approved_memory(
            client, alice, pid, title="Farm visits",
            description="We visited the farm every summer as children.",
        )

        exact_text = "Farm visits\n\nWe visited the farm every summer as children."
        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": exact_text, "mode": "dense"},
            headers=alice,
        )
        body = r.json()
        assert body["items"][0]["memory_id"] == m["id"]
        assert body["items"][0]["score"] > 0.99  # ~identical vector -> cosine similarity ~1

    def test_dense_mode_without_a_provider_returns_empty_with_a_diagnostic_not_an_error(
        self, client, alice
    ):
        pid = profile_id(client, alice)
        self._approved_memory(client, alice, pid)  # approved with no provider -> chunk pending

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "anything", "mode": "dense"},
            headers=alice,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []
        assert "embedding provider" in r.json()["diagnostics"]["dense_error"].lower()

    def test_keyword_mode_still_finds_a_pending_unembedded_chunk(self, client, alice):
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="Sunday breakfast", description="Mum always made poha."
        )  # no provider configured -> chunk stays pending, not embedded

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "poha", "mode": "keyword"},
            headers=alice,
        )
        assert len(r.json()["items"]) == 1

    def test_keyword_search_matches_a_full_natural_language_question(self, client, alice):
        """Regression test for the fix found while running evals/run_retrieval_eval.py: the
        original AND-every-word query matched nothing for a real question, since words like
        "what"/"did"/"for" never appear in the chunk text. See docs/decisions/0006."""
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="Sunday breakfast",
            description="Mum always made poha every Sunday morning.",
        )

        r = client.post(
            "/api/v1/retrieval/search",
            json={
                "person_profile_id": pid,
                "query": "What did Mum make for breakfast on Sundays?",
                "mode": "keyword",
            },
            headers=alice,
        )
        assert len(r.json()["items"]) == 1

    def test_category_filter_excludes_non_matching_memories(self, client, alice, monkeypatch):
        patch_all_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="Family trip", description="Trip to Goa", category="family"
        )
        self._approved_memory(
            client, alice, pid, title="Daily routine", description="Morning walk",
            category="daily_life",
        )

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "trip", "category": "family"},
            headers=alice,
        )
        titles = {item["metadata"]["title"] for item in r.json()["items"]}
        assert titles == {"Family trip"}

    def test_a_filter_matching_nothing_returns_no_items_not_an_error(self, client, alice):
        pid = profile_id(client, alice)
        self._approved_memory(client, alice, pid, category="family")

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "anything", "category": "no_such_category"},
            headers=alice,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_search_is_scoped_to_the_profiles_own_approved_memories(
        self, client, alice, bob, monkeypatch
    ):
        patch_all_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        self._approved_memory(
            client, alice, pid, title="Secret", description="Something only Alice should see."
        )

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "secret"},
            headers=bob,
        )
        assert r.status_code == 404  # Bob doesn't own this profile at all

    def test_draft_and_awaiting_review_memories_are_never_returned(self, client, alice):
        pid = profile_id(client, alice)
        make_memory(client, alice, pid, title="Not yet reviewed", description="Still a draft")

        r = client.post(
            "/api/v1/retrieval/search",
            json={"person_profile_id": pid, "query": "draft", "mode": "keyword"},
            headers=alice,
        )
        assert r.json()["items"] == []

    def test_requires_authentication(self, client):
        r = client.post(
            "/api/v1/retrieval/search", json={"person_profile_id": str(uuid4()), "query": "x"}
        )
        assert r.status_code == 401
