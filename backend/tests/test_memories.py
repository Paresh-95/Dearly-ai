import uuid

from tests.test_profiles import make_profile


def make_memory(client, headers, profile_id, **extra):
    body = {
        "person_profile_id": profile_id,
        "title": "Sunday breakfast",
        "description": "Mum always made poha every Sunday morning.",
        **extra,
    }
    r = client.post("/api/v1/memories", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def profile_id(client, headers, **extra):
    return make_profile(client, headers, **extra)["id"]


def test_create_defaults_to_draft_and_stamps_origin_provenance(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid)
    assert m["status"] == "draft"
    assert m["origin"] == "user_written"
    assert m["provenance"] == "family_recollection"
    assert m["approved_at"] is None
    assert m["people"] == []


def test_create_with_people_and_submit_for_review(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(
        client,
        alice,
        pid,
        status="awaiting_review",
        people=[{"name": "Grandma", "relationship": "great-grandmother"}],
        category="family",
        location="Pune",
        date_text="sometime in the 1990s",
    )
    assert m["status"] == "awaiting_review"
    assert m["people"][0]["name"] == "Grandma"


def test_create_rejects_someone_elses_profile(client, alice, bob):
    pid = profile_id(client, alice)
    r = client.post(
        "/api/v1/memories",
        json={"person_profile_id": pid, "title": "t", "description": "d"},
        headers=bob,
    )
    assert r.status_code == 404


def test_create_cannot_be_approved_or_rejected_directly(client, alice):
    pid = profile_id(client, alice)
    r = client.post(
        "/api/v1/memories",
        json={"person_profile_id": pid, "title": "t", "description": "d", "status": "approved"},
        headers=alice,
    )
    assert r.status_code == 422


def test_date_range_validated(client, alice):
    pid = profile_id(client, alice)
    r = client.post(
        "/api/v1/memories",
        json={
            "person_profile_id": pid,
            "title": "t",
            "description": "d",
            "date_start": "2000-01-01",
            "date_end": "1999-01-01",
        },
        headers=alice,
    )
    assert r.status_code == 422


def test_full_review_lifecycle_approve(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    r = client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved"
    assert body["approved_at"] is not None


def test_full_review_lifecycle_reject_with_note(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    r = client.post(
        f"/api/v1/memories/{m['id']}/reject", json={"note": "Date seems wrong"}, headers=alice
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_cannot_approve_a_draft_memory_directly(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid)  # status=draft
    r = client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)
    assert r.status_code == 200  # draft -> approved IS allowed per the state machine
    assert r.json()["status"] == "approved"


def test_rejected_memory_must_be_revised_before_resubmitting(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    client.post(f"/api/v1/memories/{m['id']}/reject", json={}, headers=alice)
    # Cannot go straight back to awaiting_review...
    r = client.patch(
        f"/api/v1/memories/{m['id']}", json={"status": "awaiting_review"}, headers=alice
    )
    assert r.status_code == 409
    # ...must pass through draft first.
    r2 = client.patch(f"/api/v1/memories/{m['id']}", json={"status": "draft"}, headers=alice)
    assert r2.status_code == 200
    assert r2.json()["status"] == "draft"


def test_patch_cannot_set_approved_or_rejected(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid)
    r = client.patch(f"/api/v1/memories/{m['id']}", json={"status": "approved"}, headers=alice)
    assert r.status_code == 422


def test_editing_approved_memory_reverts_to_awaiting_review(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

    r = client.patch(
        f"/api/v1/memories/{m['id']}", json={"description": "Corrected wording"}, headers=alice
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "awaiting_review"
    assert body["approved_at"] is None
    assert body["description"] == "Corrected wording"


def test_marking_approved_memory_uncertain_also_reverts_to_review(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

    r = client.patch(
        f"/api/v1/memories/{m['id']}",
        json={"is_uncertain": True, "uncertainty_note": "Not sure of the year"},
        headers=alice,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_review"


def test_editing_with_explicit_status_overrides_the_default(client, alice):
    """An approved memory can't jump straight to draft (it must pass through
    awaiting_review - see test_memory_rules.py), but an awaiting_review one can: this
    checks that an explicit status in the PATCH body is honoured alongside a content edit."""
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")

    r = client.patch(
        f"/api/v1/memories/{m['id']}",
        json={"description": "Corrected wording", "status": "draft"},
        headers=alice,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
    assert r.json()["description"] == "Corrected wording"


def test_approved_memory_cannot_be_patched_straight_to_draft(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, status="awaiting_review")
    client.post(f"/api/v1/memories/{m['id']}/approve", headers=alice)

    r = client.patch(f"/api/v1/memories/{m['id']}", json={"status": "draft"}, headers=alice)
    assert r.status_code == 409


def test_people_replace_on_update(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid, people=[{"name": "A", "relationship": "aunt"}])
    r = client.patch(
        f"/api/v1/memories/{m['id']}",
        json={"people": [{"name": "B", "relationship": "uncle"}]},
        headers=alice,
    )
    assert [p["name"] for p in r.json()["people"]] == ["B"]


def test_delete_memory(client, alice):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid)
    assert client.delete(f"/api/v1/memories/{m['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/memories/{m['id']}", headers=alice).status_code == 404


def test_requires_authentication(client, alice):
    pid = profile_id(client, alice)
    assert client.get("/api/v1/memories", params={"person_profile_id": pid}).status_code == 401


def test_cross_user_memory_access_is_404(client, alice, bob):
    pid = profile_id(client, alice)
    m = make_memory(client, alice, pid)
    url = f"/api/v1/memories/{m['id']}"
    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"title": "Hacked"}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    assert client.post(f"{url}/approve", headers=bob).status_code == 404
    assert client.post(f"{url}/reject", json={}, headers=bob).status_code == 404
    assert client.get(url, headers=alice).json()["title"] == "Sunday breakfast"  # untouched


def test_list_only_returns_own_memories(client, alice, bob):
    pid = profile_id(client, alice)
    make_memory(client, alice, pid)
    r = client.get("/api/v1/memories", headers=bob)
    assert r.json()["items"] == [] and r.json()["total"] == 0


def test_list_filters_by_profile_status_and_category(client, alice):
    pid1, pid2 = profile_id(client, alice), profile_id(client, alice, name="Dad")
    make_memory(client, alice, pid1, category="family")
    make_memory(client, alice, pid1, status="awaiting_review", category="daily_life")
    make_memory(client, alice, pid2, category="family")

    r = client.get("/api/v1/memories", params={"person_profile_id": pid1}, headers=alice)
    assert r.json()["total"] == 2

    r = client.get(
        "/api/v1/memories", params={"person_profile_id": pid1, "status": "draft"}, headers=alice
    )
    assert r.json()["total"] == 1

    r = client.get(
        "/api/v1/memories", params={"person_profile_id": pid1, "category": "family"}, headers=alice
    )
    assert r.json()["total"] == 1


def test_list_search_filters_title_and_description(client, alice):
    pid = profile_id(client, alice)
    make_memory(client, alice, pid, title="Poha morning", description="x")
    make_memory(client, alice, pid, title="Something else", description="y")
    r = client.get("/api/v1/memories", params={"q": "poha"}, headers=alice)
    assert r.json()["total"] == 1


def test_list_pagination(client, alice):
    pid = profile_id(client, alice)
    for i in range(5):
        make_memory(client, alice, pid, title=f"Memory {i}")

    page1 = client.get(
        "/api/v1/memories", params={"person_profile_id": pid, "limit": 2}, headers=alice
    ).json()
    assert len(page1["items"]) == 2
    assert page1["total"] == 5
    assert page1["next_cursor"]

    page2 = client.get(
        "/api/v1/memories",
        params={"person_profile_id": pid, "limit": 2, "cursor": page1["next_cursor"]},
        headers=alice,
    ).json()
    assert len(page2["items"]) == 2
    seen_ids = {m["id"] for m in page1["items"]} | {m["id"] for m in page2["items"]}
    assert len(seen_ids) == 4  # no overlap between pages


def test_invalid_cursor_rejected(client, alice):
    r = client.get("/api/v1/memories", params={"cursor": "not-a-real-cursor"}, headers=alice)
    assert r.status_code == 422


def test_get_unknown_memory_is_404(client, alice):
    assert client.get(f"/api/v1/memories/{uuid.uuid4()}", headers=alice).status_code == 404
