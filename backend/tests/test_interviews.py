from uuid import uuid4

from app.domain.enums import MemoryOrigin, Provenance
from app.services.providers.interview import FakeInterviewerQuestionGenerator
from app.services.providers.llm import FakeCandidateExtractor
from tests.test_memories import profile_id


def patch_question_generator(monkeypatch, generator=None):
    gen = generator or FakeInterviewerQuestionGenerator(max_questions=2)
    monkeypatch.setattr(
        "app.services.interview.pipeline.get_interviewer_question_generator", lambda: gen
    )
    return gen


def patch_extractor(monkeypatch, extractor=None):
    ext = extractor or FakeCandidateExtractor()
    monkeypatch.setattr("app.services.interview.pipeline.get_candidate_extractor", lambda: ext)
    return ext


def start(client, headers, pid) -> dict:
    r = client.post("/api/v1/interviews", json={"person_profile_id": pid}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def answer(client, headers, interview_id, content) -> dict:
    r = client.post(
        f"/api/v1/interviews/{interview_id}/messages", json={"content": content}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()


class TestStartingAnInterview:
    def test_opening_question_is_personalised_and_deterministic(self, client, alice):
        pid = profile_id(client, alice)
        started = start(client, alice, pid)
        assert started["message"]["role"] == "assistant"
        assert "Asha Patil" in started["message"]["content"]
        assert started["message"]["done"] is False

    def test_requires_an_owned_profile(self, client, alice, bob):
        pid = profile_id(client, alice)
        r = client.post("/api/v1/interviews", json={"person_profile_id": pid}, headers=bob)
        assert r.status_code == 404

    def test_requires_authentication(self, client):
        r = client.post("/api/v1/interviews", json={"person_profile_id": str(uuid4())})
        assert r.status_code == 401


class TestConductingAnInterview:
    def test_follow_up_questions_until_done(self, client, alice, monkeypatch):
        patch_question_generator(monkeypatch, FakeInterviewerQuestionGenerator(max_questions=2))
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]

        first = answer(client, alice, interview_id, "We used to visit the farm every summer.")
        assert first["done"] is False
        assert "question" in first["content"].lower() or "tell me more" in first["content"].lower()

        second = answer(client, alice, interview_id, "She always packed too much food.")
        assert second["done"] is True
        assert "thank you" in second["content"].lower()

    def test_unconfigured_generator_gives_an_honest_answer_not_a_500(self, client, alice):
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        body = answer(client, alice, interview_id, "Anything.")
        assert body["done"] is True
        assert "isn't configured" in body["content"]

    def test_cross_user_interview_access_is_404(self, client, alice, bob):
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        r = client.post(
            f"/api/v1/interviews/{interview_id}/messages", json={"content": "hi"}, headers=bob
        )
        assert r.status_code == 404

    def test_an_ask_conversation_is_not_reachable_as_an_interview(self, client, alice):
        pid = profile_id(client, alice)
        convo = client.post(
            "/api/v1/conversations", json={"person_profile_id": pid}, headers=alice
        ).json()
        r = client.post(
            f"/api/v1/interviews/{convo['id']}/messages", json={"content": "hi"}, headers=alice
        )
        assert r.status_code == 404


class TestCompletingAnInterview:
    def test_completing_creates_review_ready_candidates_from_the_transcript(
        self, client, alice, monkeypatch
    ):
        patch_extractor(monkeypatch)
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        answer(
            client, alice, interview_id,
            "We used to visit the farm every summer and she packed far too much food for the trip.",
        )

        r = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=alice)
        assert r.status_code == 200
        candidates = r.json()["candidates"]
        assert len(candidates) == 1
        assert candidates[0]["status"] == "awaiting_review"
        assert candidates[0]["origin"] == MemoryOrigin.INTERVIEW.value
        assert candidates[0]["provenance"] == Provenance.FAMILY_RECOLLECTION.value

        # It shows up in the ordinary review queue unchanged -- no new UI needed.
        review = client.get(
            "/api/v1/memories",
            params={"person_profile_id": pid, "status": "awaiting_review"},
            headers=alice,
        ).json()
        assert any(m["id"] == candidates[0]["id"] for m in review["items"])

    def test_completing_twice_is_rejected_not_duplicated(self, client, alice, monkeypatch):
        patch_extractor(monkeypatch)
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        answer(client, alice, interview_id, "A memory worth keeping, with enough detail in it.")

        first = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=alice)
        assert first.status_code == 200
        second = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=alice)
        assert second.status_code == 409

    def test_completing_with_no_answers_yet_is_rejected(self, client, alice):
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        r = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=alice)
        assert r.status_code == 409

    def test_completing_without_a_provider_is_a_clean_503_and_stays_retryable(self, client, alice):
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        answer(client, alice, interview_id, "Something memorable happened that day.")

        r = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=alice)
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "service_unavailable"

    def test_cross_user_cannot_complete_someone_elses_interview(self, client, alice, bob):
        pid = profile_id(client, alice)
        interview_id = start(client, alice, pid)["conversation_id"]
        r = client.post(f"/api/v1/interviews/{interview_id}/complete", headers=bob)
        assert r.status_code == 404
