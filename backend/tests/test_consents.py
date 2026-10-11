from tests.test_profiles import make_profile


def test_record_account_level_consent(client, alice):
    r = client.post(
        "/api/v1/consents",
        json={"consent_type": "data_processing", "granted": True, "policy_version": "v1"},
        headers=alice,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["granted"] is True and body["person_profile_id"] is None

    listed = client.get("/api/v1/consents", headers=alice).json()["items"]
    assert len(listed) == 1


def test_consent_is_append_only_not_overwritten(client, alice):
    for granted in (True, False, True):
        client.post(
            "/api/v1/consents",
            json={"consent_type": "data_processing", "granted": granted, "policy_version": "v1"},
            headers=alice,
        )
    items = client.get("/api/v1/consents", headers=alice).json()["items"]
    assert len(items) == 3
    assert items[0]["granted"] is True  # most recent first


def test_profile_scoped_consent_requires_owned_profile(client, alice, bob):
    profile = make_profile(client, alice)
    ok = client.post(
        "/api/v1/consents",
        json={
            "consent_type": "voice_synthesis",
            "granted": False,
            "policy_version": "v1",
            "person_profile_id": profile["id"],
        },
        headers=alice,
    )
    assert ok.status_code == 201

    forbidden = client.post(
        "/api/v1/consents",
        json={
            "consent_type": "voice_synthesis",
            "granted": True,
            "policy_version": "v1",
            "person_profile_id": profile["id"],
        },
        headers=bob,
    )
    assert forbidden.status_code == 404


def test_consents_require_authentication(client):
    assert client.get("/api/v1/consents").status_code == 401


def test_consents_are_isolated_per_user(client, alice, bob):
    client.post(
        "/api/v1/consents",
        json={"consent_type": "data_processing", "granted": True, "policy_version": "v1"},
        headers=alice,
    )
    assert client.get("/api/v1/consents", headers=bob).json()["items"] == []


def test_invalid_consent_type_rejected(client, alice):
    r = client.post(
        "/api/v1/consents",
        json={"consent_type": "not_a_real_type", "granted": True, "policy_version": "v1"},
        headers=alice,
    )
    assert r.status_code == 422
