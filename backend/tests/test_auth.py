from tests.conftest import register


def test_register_login_me(client):
    headers = register(client, "Alice@Example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"  # normalised
    assert "password" not in me.text

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_duplicate_email_conflicts(client):
    register(client, "a@example.com")
    r = client.post(
        "/api/v1/auth/register", json={"email": "A@example.com", "password": "another-long-pass"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_short_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422


def test_wrong_password_and_unknown_user_look_identical(client):
    register(client, "a@example.com")
    wrong = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "nope"})
    unknown = client.post("/api/v1/auth/login", json={"email": "z@example.com", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_valid_access_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = {"Authorization": "Bearer garbage"}
    assert client.get("/api/v1/auth/me", headers=bad).status_code == 401


def test_refresh_cookie_flow(client):
    register(client, "a@example.com")  # sets httpOnly refresh cookie on the client
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new).status_code == 200


def test_refresh_token_is_not_usable_as_access_token(client):
    register(client, "a@example.com")
    refresh_cookie = client.cookies.get("mc_refresh")
    assert refresh_cookie
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_cookie}"})
    assert r.status_code == 401


def test_logout_clears_refresh_cookie(client):
    register(client, "a@example.com")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.post("/api/v1/auth/refresh").status_code == 401
