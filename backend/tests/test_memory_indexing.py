from sqlalchemy.orm import Session

from app.repositories import memory_chunks as chunks_repo
from app.services.providers.embeddings import FakeEmbeddingProvider
from tests.test_memories import make_memory, profile_id


def fake_provider():
    return FakeEmbeddingProvider()


def patch_embeddings(monkeypatch):
    monkeypatch.setattr("app.repositories.memory_chunks.get_embedding_provider", fake_provider)


class TestApproveTriggersIndexing:
    def test_approving_creates_indexed_chunks(self, client, alice, monkeypatch):
        patch_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

        chunks = client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"]
        assert len(chunks) == 1
        assert chunks[0]["index_status"] == "indexed"
        assert chunks[0]["embedding_model"] == "fake-embedding-v1"
        assert chunks[0]["meta"]["title"] == "Sunday breakfast"

    def test_approving_without_a_provider_still_approves_but_leaves_chunks_pending(
        self, client, alice
    ):
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        r = client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"  # approval is not blocked by indexing

        chunks = client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"]
        assert len(chunks) == 1
        assert chunks[0]["index_status"] == "pending"
        assert chunks[0]["embedding_model"] is None

    def test_reindex_endpoint_retries_pending_chunks_once_a_provider_is_available(
        self, client, alice, monkeypatch
    ):
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)  # no provider yet

        patch_embeddings(monkeypatch)
        r = client.post(f"/api/v1/memories/{m['id']}/reindex", headers=alice)
        assert r.status_code == 200
        assert r.json()["items"][0]["index_status"] == "indexed"

    def test_reindex_requires_approved_status(self, client, alice):
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid)  # draft
        r = client.post(f"/api/v1/memories/{m['id']}/reindex", headers=alice)
        assert r.status_code == 409


class TestLeavingApprovedClearsChunks:
    def test_editing_an_approved_memory_clears_chunks_until_reapproved(
        self, client, alice, monkeypatch
    ):
        patch_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

        r = client.patch(
            f"/api/v1/memories/{m['id']}", json={"description": "Updated text."}, headers=alice
        )
        assert r.json()["status"] == "awaiting_review"
        assert client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"] == []

        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)
        chunks = client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"]
        assert "Updated text." in chunks[0]["text"]

    def test_rejecting_an_approved_memory_clears_chunks(self, client, alice, monkeypatch):
        patch_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)
        assert client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"]

        client.post(f"/api/v1/memories/{m['id']}/reject", json={}, headers=alice)
        assert client.get(f"/api/v1/memories/{m['id']}/chunks", headers=alice).json()["items"] == []


class TestChunksAreIsolatedPerUser:
    def test_chunks_endpoint_is_404_for_another_user(self, client, alice, bob, monkeypatch):
        patch_embeddings(monkeypatch)
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")
        client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

        assert client.get(f"/api/v1/memories/{m['id']}/chunks", headers=bob).status_code == 404
        assert client.post(f"/api/v1/memories/{m['id']}/reindex", headers=bob).status_code == 404


class TestIdempotentReindexing:
    """Repository-level: directly counts embedding-provider calls across repeated
    reindex_memory() runs, which the brief's "0 new embeddings on identical re-run"
    acceptance criterion is really about."""

    def test_unchanged_content_triggers_no_new_embedding_calls(self, client, alice, engine):
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")

        calls = {"n": 0}

        class CountingProvider(FakeEmbeddingProvider):
            def embed(self, texts):
                calls["n"] += 1
                return super().embed(texts)

        with Session(engine) as db:
            from app.models import Memory

            memory = db.get(Memory, m["id"])
            chunks_repo.reindex_memory(db, memory, get_provider=CountingProvider)
            db.commit()
            assert calls["n"] == 1

            # Re-run against the exact same, unchanged content.
            chunks_repo.reindex_memory(db, memory, get_provider=CountingProvider)
            db.commit()
            assert calls["n"] == 1  # no new embedding calls for unchanged chunks

    def test_changed_content_does_trigger_a_new_embedding_call(self, client, alice, engine):
        pid = profile_id(client, alice)
        m = make_memory(client, alice, pid, status="awaiting_review")

        calls = {"n": 0}

        class CountingProvider(FakeEmbeddingProvider):
            def embed(self, texts):
                calls["n"] += 1
                return super().embed(texts)

        with Session(engine) as db:
            from app.models import Memory

            memory = db.get(Memory, m["id"])
            chunks_repo.reindex_memory(db, memory, get_provider=CountingProvider)
            db.commit()

            memory.description = "Completely different content now."
            db.flush()
            chunks_repo.reindex_memory(db, memory, get_provider=CountingProvider)
            db.commit()
            assert calls["n"] == 2


class TestShrinkingAMemoryDropsExtraChunks:
    def test_fewer_chunks_after_shortening_a_long_memory(self, client, alice, engine, monkeypatch):
        from app.core import config

        monkeypatch.setenv("MC_CHUNK_MAX_CHARS", "120")
        config.get_settings.cache_clear()
        try:
            pid = profile_id(client, alice)
            long_description = " ".join(
                f"This is sentence number {i} in a long family story." for i in range(20)
            )
            m = make_memory(
                client, alice, pid, status="awaiting_review", description=long_description
            )

            with Session(engine) as db:
                from app.models import Memory

                memory = db.get(Memory, m["id"])
                before = chunks_repo.reindex_memory(db, memory, get_provider=fake_provider)
                db.commit()
                assert len(before) > 1

                memory.description = "Much shorter now."
                db.flush()
                after = chunks_repo.reindex_memory(db, memory, get_provider=fake_provider)
                db.commit()
                assert len(after) == 1
                assert len(chunks_repo.list_for_memory(db, memory.id)) == 1
        finally:
            config.get_settings.cache_clear()
