"""Auth endpoint tests — registration, login, token revocation, password reset."""
import uuid
from datetime import datetime, timezone, timedelta

import jwt
import pytest

from hymnarranger.auth.security import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    generate_reset_token,
    hash_token,
)
from hymnarranger.db.models import PasswordResetToken
from tests.conftest import bearer


# ── Registration ───────────────────────────────────────────────────────────────

def test_register_returns_generic_message(auth_client):
    r = auth_client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 201
    assert "message" in r.json()


def test_register_duplicate_email_still_returns_201(auth_client, make_user):
    make_user(email="dup@example.com")
    r = auth_client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 201


# ── Login ──────────────────────────────────────────────────────────────────────

def test_login_returns_access_token(auth_client, make_user):
    make_user(email="login@example.com", password="Passw0rd!", verified=True)
    r = auth_client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_returns_401(auth_client, make_user):
    make_user(email="wrong@example.com", password="CorrectPass1!")
    r = auth_client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass1!"},
    )
    assert r.status_code == 401


def test_login_unverified_user_returns_403(auth_client, make_user):
    make_user(email="unverified@example.com", password="Passw0rd!", verified=False)
    r = auth_client.post(
        "/auth/login",
        json={"email": "unverified@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 403


def test_login_nonexistent_email_returns_401(auth_client):
    r = auth_client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 401


# ── /auth/me ───────────────────────────────────────────────────────────────────

def test_me_without_token_returns_403(auth_client):
    r = auth_client.get("/auth/me")
    assert r.status_code in (401, 403)


def test_me_with_malformed_sub_returns_401(auth_client):
    bad_token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    r = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 401


# ── Token revocation after password change ─────────────────────────────────────

def test_token_issued_before_password_change_returns_401(
    auth_client, make_user, db_session
):
    user = make_user(email="revoke@example.com")
    stale_iat = datetime.now(timezone.utc) - timedelta(minutes=5)
    user.password_changed_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    db_session.commit()

    stale_token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": stale_iat,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    r = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {stale_token}"},
    )
    assert r.status_code == 401


def test_fresh_token_after_password_change_succeeds(
    auth_client, make_user, db_session
):
    user = make_user(email="fresh@example.com")
    user.password_changed_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    db_session.commit()

    r = auth_client.get("/auth/me", headers=bearer(user))
    assert r.status_code == 200


# ── Password reset ─────────────────────────────────────────────────────────────

def test_expired_reset_token_returns_400(auth_client, make_user, db_session):
    user = make_user(email="expire@example.com")
    raw_token, token_hash = generate_reset_token()
    db_session.add(PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    db_session.commit()

    r = auth_client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 400


def test_used_reset_token_returns_400(auth_client, make_user, db_session):
    user = make_user(email="used@example.com")
    raw_token, token_hash = generate_reset_token()
    db_session.add(PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used=True,
    ))
    db_session.commit()

    r = auth_client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 400


def test_valid_reset_token_changes_password(auth_client, make_user, db_session):
    user = make_user(email="reset@example.com", password="OldPass1!")
    raw_token, token_hash = generate_reset_token()
    db_session.add(PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    ))
    db_session.commit()

    r = auth_client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPass1!"},
    )
    assert r.status_code == 200

    r2 = auth_client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "NewPass1!"},
    )
    assert r2.status_code == 200
