"""Phase 10A: end-to-end tests through the live HTTP API for
POST /api/auth/register, POST /api/auth/login, and GET /api/auth/me.

These go through the app's own get_db dependency (a real, committing
session), so created users are cleaned up via the cleanup_users fixture,
mirroring tests/test_resume_api_persistence.py's approach.
"""

import time

import jwt

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User


def _register(client, cleanup_users, email="new.user@example.com", password="s3cur3-password", full_name=None):
    payload = {"email": email, "password": password}
    if full_name is not None:
        payload["full_name"] = full_name
    response = client.post("/api/auth/register", json=payload)
    if response.status_code == 200:
        cleanup_users.append(response.json()["id"])
    return response


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------


def test_register_success(client, cleanup_users):
    response = _register(client, cleanup_users, email="alice@example.com", full_name="Alice Example")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice Example"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


def test_register_duplicate_email_is_rejected(client, cleanup_users):
    first = _register(client, cleanup_users, email="bob@example.com")
    assert first.status_code == 200

    second = client.post("/api/auth/register", json={"email": "bob@example.com", "password": "another-password"})
    assert second.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post("/api/auth/register", json={"email": "not-an-email", "password": "s3cur3-password"})
    assert response.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post("/api/auth/register", json={"email": "shortpw@example.com", "password": "short"})
    assert response.status_code == 422


def test_register_response_never_contains_password_fields(client, cleanup_users):
    response = _register(client, cleanup_users, email="nopass@example.com", password="s3cur3-password")
    assert response.status_code == 200
    body_text = response.text.lower()
    assert "password" not in body_text
    assert "s3cur3-password" not in response.text
    assert "hash" not in body_text


def test_register_password_never_stored_in_plaintext(client, cleanup_users):
    response = _register(client, cleanup_users, email="plaintext@example.com", password="s3cur3-password")
    user_id = response.json()["id"]

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        assert user.password_hash != "s3cur3-password"
        assert user.password_hash.startswith("$argon2id$")
    finally:
        session.close()


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------


def test_login_success(client, cleanup_users):
    _register(client, cleanup_users, email="loginok@example.com", password="s3cur3-password")

    response = client.post("/api/auth/login", json={"email": "loginok@example.com", "password": "s3cur3-password"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_expire_minutes * 60
    assert len(body["access_token"]) > 20


def test_login_rejects_wrong_password(client, cleanup_users):
    _register(client, cleanup_users, email="wrongpw@example.com", password="s3cur3-password")

    response = client.post("/api/auth/login", json={"email": "wrongpw@example.com", "password": "not-the-password"})
    assert response.status_code == 401


def test_login_rejects_unknown_user(client):
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever123"})
    assert response.status_code == 401


def test_login_response_never_contains_password_fields(client, cleanup_users):
    _register(client, cleanup_users, email="loginsafe@example.com", password="s3cur3-password")
    response = client.post("/api/auth/login", json={"email": "loginsafe@example.com", "password": "s3cur3-password"})
    assert "password" not in response.text.lower()


# --------------------------------------------------------------------------
# GET /api/auth/me
# --------------------------------------------------------------------------


def test_me_with_valid_token_returns_current_user(client, cleanup_users):
    _register(client, cleanup_users, email="me@example.com", password="s3cur3-password", full_name="Me Example")
    login_resp = client.post("/api/auth/login", json={"email": "me@example.com", "password": "s3cur3-password"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Me Example"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


def test_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_malformed_token_returns_401(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer this-is-not-a-jwt"})
    assert response.status_code == 401


def test_me_with_expired_token_returns_401(client, cleanup_users):
    register_resp = _register(client, cleanup_users, email="expired@example.com", password="s3cur3-password")
    user_id = register_resp.json()["id"]

    settings = get_settings()
    now = time.time()
    expired_token = jwt.encode(
        {"sub": user_id, "email": "expired@example.com", "type": "access", "iat": now - 120, "exp": now - 60},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_me_with_wrong_signature_token_returns_401(client, cleanup_users):
    register_resp = _register(client, cleanup_users, email="forged@example.com", password="s3cur3-password")
    user_id = register_resp.json()["id"]

    settings = get_settings()
    now = time.time()
    forged_token = jwt.encode(
        {"sub": user_id, "email": "forged@example.com", "type": "access", "iat": now, "exp": now + 60},
        "a-completely-different-secret-that-is-not-the-real-one",
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert response.status_code == 401


def test_me_for_unknown_user_id_returns_401(client):
    settings = get_settings()
    now = time.time()
    token_for_nobody = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email": "nobody@example.com",
            "type": "access",
            "iat": now,
            "exp": now + 60,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_for_nobody}"})
    assert response.status_code == 401


def test_me_for_inactive_user_returns_401(client, cleanup_users):
    register_resp = _register(client, cleanup_users, email="deactivated@example.com", password="s3cur3-password")
    user_id = register_resp.json()["id"]
    login_resp = client.post(
        "/api/auth/login", json={"email": "deactivated@example.com", "password": "s3cur3-password"}
    )
    token = login_resp.json()["access_token"]

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        user.is_active = False
        session.commit()
    finally:
        session.close()

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Security: secrets never leak
# --------------------------------------------------------------------------


def test_jwt_secret_never_appears_in_any_response(client, cleanup_users):
    secret = get_settings().jwt_secret_key.get_secret_value()

    responses = [
        _register(client, cleanup_users, email="secretcheck@example.com", password="s3cur3-password"),
        client.post("/api/auth/login", json={"email": "secretcheck@example.com", "password": "s3cur3-password"}),
        client.post("/api/auth/login", json={"email": "secretcheck@example.com", "password": "wrong"}),
        client.get("/api/auth/me"),  # 401, no token
    ]
    for response in responses:
        assert secret not in response.text
