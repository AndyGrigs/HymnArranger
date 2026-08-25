"""Works endpoint tests — ownership isolation and basic CRUD."""
from tests.conftest import bearer


# ── Isolation: other user's work must return 404 ──────────────────────────────

def test_get_foreign_work_returns_404(auth_client, make_user, make_work):
    alice = make_user(email="alice@example.com")
    bob = make_user(email="bob@example.com")
    work = make_work(alice)

    r = auth_client.get(f"/works/{work.id}", headers=bearer(bob))
    assert r.status_code == 404


def test_patch_foreign_work_returns_404(auth_client, make_user, make_work):
    alice = make_user(email="alice2@example.com")
    bob = make_user(email="bob2@example.com")
    work = make_work(alice)

    r = auth_client.patch(
        f"/works/{work.id}",
        json={"title": "stolen title"},
        headers=bearer(bob),
    )
    assert r.status_code == 404


def test_delete_foreign_work_returns_404(auth_client, make_user, make_work):
    alice = make_user(email="alice3@example.com")
    bob = make_user(email="bob3@example.com")
    work = make_work(alice)

    r = auth_client.delete(f"/works/{work.id}", headers=bearer(bob))
    assert r.status_code == 404


# ── Owner can access their own work ───────────────────────────────────────────

def test_owner_can_get_work(auth_client, make_user, make_work):
    alice = make_user(email="owner@example.com")
    work = make_work(alice, title="My Hymn")

    r = auth_client.get(f"/works/{work.id}", headers=bearer(alice))
    assert r.status_code == 200
    assert r.json()["title"] == "My Hymn"


def test_owner_can_rename_work(auth_client, make_user, make_work):
    alice = make_user(email="rename@example.com")
    work = make_work(alice, title="Old Title")

    r = auth_client.patch(
        f"/works/{work.id}",
        json={"title": "New Title"},
        headers=bearer(alice),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"


def test_owner_can_delete_work(auth_client, make_user, make_work):
    alice = make_user(email="delete@example.com")
    work = make_work(alice)

    r = auth_client.delete(f"/works/{work.id}", headers=bearer(alice))
    assert r.status_code == 200

    r2 = auth_client.get(f"/works/{work.id}", headers=bearer(alice))
    assert r2.status_code == 404


# ── List endpoint ─────────────────────────────────────────────────────────────

def test_list_works_only_returns_own(auth_client, make_user, make_work):
    alice = make_user(email="list-alice@example.com")
    bob = make_user(email="list-bob@example.com")
    make_work(alice, title="Alice Work")
    make_work(bob, title="Bob Work")

    r = auth_client.get("/works", headers=bearer(alice))
    assert r.status_code == 200
    titles = [w["title"] for w in r.json()["items"]]
    assert "Alice Work" in titles
    assert "Bob Work" not in titles


def test_list_works_unauthenticated_returns_403(auth_client):
    r = auth_client.get("/works")
    assert r.status_code in (401, 403)
