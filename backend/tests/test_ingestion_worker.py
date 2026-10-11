from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.enums import MemoryOrigin
from app.services.providers.llm import FakeCandidateExtractor
from app.services.providers.stt import FakeSpeechTranscriber
from app.workers.ingestion_worker import process_one
from tests.test_profiles import make_profile

FIXTURES = Path(__file__).parent / "fixtures"


def upload(client, headers, profile_id, filename, content, content_type, kind):
    return client.post(
        "/api/v1/uploads",
        data={"person_profile_id": profile_id, "kind": kind},
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def process_with_fakes(db: Session) -> bool:
    return process_one(
        db,
        "test-worker",
        get_transcriber=FakeSpeechTranscriber,
        get_extractor=FakeCandidateExtractor,
    )


class TestSuccessfulIngestion:
    def test_text_upload_produces_segments_and_a_reviewable_memory(self, client, alice, engine):
        pid = make_profile(client, alice)["id"]
        job = upload(
            client, alice, pid, "sample.txt", (FIXTURES / "sample.txt").read_bytes(),
            "text/plain", "text",
        ).json()
        source_id = client.get(
            "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
        ).json()["items"][0]["id"]

        with Session(engine) as db:
            assert process_with_fakes(db) is True

        job_after = client.get(f"/api/v1/ingestion-jobs/{job['id']}", headers=alice).json()
        assert job_after["state"] == "succeeded"
        assert job_after["progress"] == 100
        assert job_after["error"] is None

        segments = client.get(f"/api/v1/sources/{source_id}/segments", headers=alice).json()
        assert len(segments["items"]) == 3
        assert segments["items"][0]["raw_text"] == "Sunday breakfast"

        memories = client.get(
            "/api/v1/memories",
            params={"person_profile_id": pid, "status": "awaiting_review"},
            headers=alice,
        ).json()
        assert memories["total"] >= 1
        candidate = memories["items"][0]
        assert candidate["origin"] == MemoryOrigin.EXTRACTED.value
        assert candidate["provenance"] == "document"

    def test_no_queued_job_returns_false(self, engine):
        with Session(engine) as db:
            assert process_with_fakes(db) is False

    def test_whatsapp_upload_captures_sender_as_speaker(self, client, alice, engine):
        pid = make_profile(client, alice)["id"]
        upload(
            client, alice, pid, "chat.txt", (FIXTURES / "sample_whatsapp.txt").read_bytes(),
            "text/plain", "whatsapp",
        )
        source_id = client.get(
            "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
        ).json()["items"][0]["id"]

        with Session(engine) as db:
            process_with_fakes(db)

        segments = client.get(f"/api/v1/sources/{source_id}/segments", headers=alice).json()
        assert segments["items"][0]["speaker_label"] == "Asha"
        assert segments["items"][0]["speaker_verified"] is True


class TestFailureIsVisibleAndRetried:
    def test_bad_whatsapp_export_fails_with_a_clear_error_and_requeues(self, client, alice, engine):
        pid = make_profile(client, alice)["id"]
        job = upload(
            client, alice, pid, "notes.txt", (FIXTURES / "not_whatsapp.txt").read_bytes(),
            "text/plain", "whatsapp",
        ).json()

        with Session(engine) as db:
            process_with_fakes(db)

        job_after = client.get(f"/api/v1/ingestion-jobs/{job['id']}", headers=alice).json()
        assert job_after["attempts"] == 1
        assert job_after["state"] == "queued"  # still under the retry limit
        assert "WhatsApp" in job_after["error"]

    def test_job_fails_for_good_after_max_attempts(self, client, alice, engine, monkeypatch):
        from app.core import config

        monkeypatch.setenv("MC_WORKER_MAX_ATTEMPTS", "1")
        config.get_settings.cache_clear()
        try:
            pid = make_profile(client, alice)["id"]
            job = upload(
                client, alice, pid, "notes.txt", (FIXTURES / "not_whatsapp.txt").read_bytes(),
                "text/plain", "whatsapp",
            ).json()

            with Session(engine) as db:
                process_with_fakes(db)

            job_after = client.get(f"/api/v1/ingestion-jobs/{job['id']}", headers=alice).json()
            assert job_after["state"] == "failed"
            assert job_after["attempts"] == 1
        finally:
            config.get_settings.cache_clear()

    def test_missing_llm_provider_fails_the_job_without_fabricating_memories(
        self, client, alice, engine
    ):
        pid = make_profile(client, alice)["id"]
        job = upload(
            client, alice, pid, "sample.txt", (FIXTURES / "sample.txt").read_bytes(),
            "text/plain", "text",
        ).json()

        with Session(engine) as db:
            # Real provider factories: no MC_OPENAI_API_KEY is set in the test environment.
            process_one(db, "test-worker")

        job_after = client.get(f"/api/v1/ingestion-jobs/{job['id']}", headers=alice).json()
        assert job_after["state"] == "queued"
        err = job_after["error"].lower()
        assert "llm provider" in err or "speech-to-text" in err

        memories = client.get(
            "/api/v1/memories", params={"person_profile_id": pid}, headers=alice
        ).json()
        assert memories["total"] == 0  # segments may exist, but nothing was fabricated

        # The text itself was still extracted and stored even though candidate generation
        # failed -- real, useful work is not thrown away just because the next step failed.
        source_id = client.get(
            "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
        ).json()["items"][0]["id"]
        segments = client.get(f"/api/v1/sources/{source_id}/segments", headers=alice).json()
        assert len(segments["items"]) == 3
