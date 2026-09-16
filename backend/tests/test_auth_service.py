"""Phase 10A: unit + integration tests for app.core.security and
app.services.auth_service.

Password hashing/JWT tests (no DB) run as plain unit tests. User
creation/authentication tests use the db_session fixture's real-Postgres,
rolled-back-transaction pattern established in the other *_repository
test files.
"""

import time
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenException,
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services import auth_service

# --------------------------------------------------------------------------
# Password hashing (no DB)
# --------------------------------------------------------------------------


def test_hash_password_produces_argon2id_hash():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")
    assert hashed != "correct horse battery staple"


def test_hash_password_is_salted_and_nondeterministic():
    hashed_a = hash_password("same-password")
    hashed_b = hash_password("same-password")
    # Same input, different output each time - proves a random salt is
    # actually being used, not a fixed/no salt (which would make two
    # identical passwords produce identical hashes, a classic weakness).
    assert hashed_a != hashed_b


def test_verify_password_accepts_correct_password():
    hashed = hash_password("hunter2000")
    assert verify_password("hunter2000", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("hunter2000")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_malformed_hash_without_raising():
    assert verify_password("anything", "not-a-real-hash") is False


# --------------------------------------------------------------------------
# JWT (no DB)
# --------------------------------------------------------------------------


def test_create_access_token_round_trips():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, email="jane@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "jane@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_rejects_missing_token():
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token(None)
    assert exc_info.value.reason == TokenError.MISSING


def test_decode_access_token_rejects_empty_token():
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token("")
    assert exc_info.value.reason == TokenError.MISSING


def test_decode_access_token_rejects_malformed_token():
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token("this-is-not-a-jwt")
    assert exc_info.value.reason == TokenError.MALFORMED


def test_decode_access_token_rejects_wrong_signature():
    # Signed with a different secret than the app's own - a forged token.
    settings = get_settings()
    bad_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "email": "x@example.com", "type": "access", "iat": time.time(), "exp": time.time() + 60},
        "a-completely-different-secret-that-is-not-the-real-one",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token(bad_token)
    assert exc_info.value.reason == TokenError.MALFORMED


def test_decode_access_token_rejects_expired_token():
    settings = get_settings()
    now = time.time()
    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "x@example.com",
            "type": "access",
            "iat": now - 120,
            "exp": now - 60,  # expired one minute ago
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token(expired_token)
    assert exc_info.value.reason == TokenError.EXPIRED


def test_decode_access_token_rejects_wrong_token_type():
    settings = get_settings()
    now = time.time()
    wrong_type_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "email": "x@example.com", "type": "refresh", "iat": now, "exp": now + 60},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenException) as exc_info:
        decode_access_token(wrong_type_token)
    assert exc_info.value.reason == TokenError.INVALID


def test_jwt_claims_never_contain_password_or_secret():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, email="jane@example.com")
    payload = decode_access_token(token)
    assert "password" not in payload
    assert "password_hash" not in payload
    # The raw token string itself must not leak the secret either - the
    # secret is used to *sign*, never embedded as a claim or substring.
    settings = get_settings()
    assert settings.jwt_secret_key.get_secret_value() not in token


# --------------------------------------------------------------------------
# create_user / authenticate_user (DB)
# --------------------------------------------------------------------------


def test_create_user_persists_row_with_hashed_password(db_session):
    user = auth_service.create_user(db_session, email="new.user@example.com", password="s3cur3-password")

    assert user.id is not None
    assert user.email == "new.user@example.com"
    assert user.is_active is True

    fetched = db_session.get(User, user.id)
    assert fetched is not None
    # The whole point: password_hash is populated and is NOT the plaintext.
    assert fetched.password_hash != "s3cur3-password"
    assert fetched.password_hash.startswith("$argon2id$")


def test_create_user_rejects_duplicate_email(db_session):
    auth_service.create_user(db_session, email="dupe@example.com", password="s3cur3-password")
    with pytest.raises(auth_service.EmailAlreadyRegisteredError):
        auth_service.create_user(db_session, email="dupe@example.com", password="another-password")


def test_authenticate_user_with_correct_credentials(db_session):
    auth_service.create_user(db_session, email="auth@example.com", password="correct-password")
    user = auth_service.authenticate_user(db_session, email="auth@example.com", password="correct-password")
    assert user.email == "auth@example.com"


def test_authenticate_user_rejects_wrong_password(db_session):
    auth_service.create_user(db_session, email="auth2@example.com", password="correct-password")
    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.authenticate_user(db_session, email="auth2@example.com", password="wrong-password")


def test_authenticate_user_rejects_unknown_email(db_session):
    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.authenticate_user(db_session, email="nobody@example.com", password="whatever")


def test_authenticate_user_rejects_inactive_user(db_session):
    user = auth_service.create_user(db_session, email="inactive@example.com", password="correct-password")
    user.is_active = False
    db_session.flush()

    with pytest.raises(auth_service.InactiveUserError):
        auth_service.authenticate_user(db_session, email="inactive@example.com", password="correct-password")
