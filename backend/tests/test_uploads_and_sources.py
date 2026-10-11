from pathlib import Path

from tests.test_profiles import make_profile

FIXTURES = Path(__file__).parent / "fixtures"


def profile_id(client, headers):
    return make_profile(client, headers)["id"]


def upload(client, headers, profile_id, filename, content, content_type, kind, **extra):
    return client.post(
        "/api/v1/uploads",
        data={"person_profile_id": profile_id, "kind": kind, **extra},
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def test_upload_creates_a_queued_job(client, alice):
    pid = profile_id(client, alice)
    content = (FIXTURES / "sample.txt").read_bytes()
    r = upload(client, alice, pid, "sample.txt", content, "text/plain", "text")
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["state"] == "queued"
    assert job["attempts"] == 0

    src = client.get("/api/v1/sources", params={"person_profile_id": pid}, headers=alice).json()
    assert src["items"][0]["kind"] == "text"
    assert src["items"][0]["filename"] == "sample.txt"


def test_upload_rejects_a_mismatched_file_type(client, alice):
    pid = profile_id(client, alice)
    r = upload(client, alice, pid, "sample.pdf", b"not a pdf at all", "application/pdf", "pdf")
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media"


def test_upload_rejects_a_file_over_the_configured_size_cap(client, alice, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("MC_MAX_UPLOAD_MB", "0")  # 0 MB: any non-empty file is "too large"
    get_settings.cache_clear()
    try:
        pid = profile_id(client, alice)
        r = upload(client, alice, pid, "sample.txt", b"just a few bytes", "text/plain", "text")
        assert r.status_code == 413
        assert r.json()["error"]["code"] == "too_large"
    finally:
        get_settings.cache_clear()  # restore the default for every later test


def test_upload_cannot_target_someone_elses_profile(client, alice, bob):
    pid = profile_id(client, alice)
    r = upload(client, bob, pid, "sample.txt", b"hello", "text/plain", "text")
    assert r.status_code == 404


def test_upload_rejects_manual_as_a_kind(client, alice):
    pid = profile_id(client, alice)
    r = upload(client, alice, pid, "sample.txt", b"hello", "text/plain", "manual")
    assert r.status_code == 422


def test_requires_authentication(client):
    assert client.get("/api/v1/sources").status_code == 401
    assert client.get("/api/v1/ingestion-jobs").status_code == 401


def test_source_download_round_trips_the_original_bytes(client, alice):
    pid = profile_id(client, alice)
    content = (FIXTURES / "sample.txt").read_bytes()
    upload(client, alice, pid, "sample.txt", content, "text/plain", "text")
    source_id = client.get(
        "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
    ).json()["items"][0]["id"]
    assert source_id  # sanity

    r = client.get(f"/api/v1/sources/{source_id}/download", headers=alice)
    assert r.status_code == 200
    assert r.content == content
    assert "attachment" in r.headers["content-disposition"]


def test_source_and_job_are_isolated_per_user(client, alice, bob):
    pid = profile_id(client, alice)
    job = upload(
        client, alice, pid, "sample.txt", b"hello there", "text/plain", "text"
    ).json()
    source_id = client.get(
        "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
    ).json()["items"][0]["id"]

    assert client.get(f"/api/v1/sources/{source_id}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/sources/{source_id}/download", headers=bob).status_code == 404
    assert client.get(f"/api/v1/sources/{source_id}/segments", headers=bob).status_code == 404
    assert client.get(f"/api/v1/ingestion-jobs/{job['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/v1/sources/{source_id}", headers=bob).status_code == 404


def test_deleting_a_source_removes_it(client, alice):
    pid = profile_id(client, alice)
    upload(client, alice, pid, "sample.txt", b"hello there", "text/plain", "text")
    source_id = client.get(
        "/api/v1/sources", params={"person_profile_id": pid}, headers=alice
    ).json()["items"][0]["id"]

    assert client.delete(f"/api/v1/sources/{source_id}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/sources/{source_id}", headers=alice).status_code == 404
