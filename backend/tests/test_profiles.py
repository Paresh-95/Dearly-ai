import uuid

PROFILE = {"name": "Asha Patil", "relationship": "mother"}


def make_profile(client, headers, **extra):
    r = client.post("/api/v1/profiles", json={**PROFILE, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_with_only_required_fields(client, alice):
    p = make_profile(client, alice)
    assert p["name"] == "Asha Patil"
    assert p["languages"] == [] and p["birth_date"] is None


def test_create_full_profile_and_list(client, alice):
    make_profile(
        client, alice, preferred_name="Aai", languages=["Marathi", "English"],
        favourite_expressions=["Chalo, chalo!"], birth_date="1960-03-01", death_date="2024-05-02",
    )
    items = client.get("/api/v1/profiles", headers=alice).json()["items"]
    assert len(items) == 1 and items[0]["preferred_name"] == "Aai"


def test_dates_validated(client, alice):
    r = client.post(
        "/api/v1/profiles",
        json={**PROFILE, "birth_date": "2000-01-01", "death_date": "1990-01-01"},
        headers=alice,
    )
    assert r.status_code == 422


def test_patch_updates_only_given_fields(client, alice):
    p = make_profile(client, alice, biography="Original bio")
    r = client.patch(f"/api/v1/profiles/{p['id']}", json={"preferred_name": "Aai"}, headers=alice)
    assert r.status_code == 200
    assert r.json()["preferred_name"] == "Aai"
    assert r.json()["biography"] == "Original bio"


def test_patch_cannot_null_required_fields(client, alice):
    p = make_profile(client, alice)
    r = client.patch(f"/api/v1/profiles/{p['id']}", json={"name": None}, headers=alice)
    assert r.status_code == 200
    assert r.json()["name"] == "Asha Patil"


def test_requires_authentication(client):
    assert client.get("/api/v1/profiles").status_code == 401
    assert client.post("/api/v1/profiles", json=PROFILE).status_code == 401


def test_cross_user_access_is_404_not_403(client, alice, bob):
    p = make_profile(client, alice)
    url = f"/api/v1/profiles/{p['id']}"
    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"name": "Hacked"}, headers=bob).status_code == 404
    assert client.get(url, headers=alice).json()["name"] == "Asha Patil"  # untouched
    missing = client.get(f"/api/v1/profiles/{uuid.uuid4()}", headers=bob)
    assert missing.json() == client.get(url, headers=bob).json()  # same response as missing


def test_list_only_returns_own_profiles(client, alice, bob):
    make_profile(client, alice)
    assert client.get("/api/v1/profiles", headers=bob).json()["items"] == []
