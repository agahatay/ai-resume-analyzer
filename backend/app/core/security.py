"""Password hashing and JWT primitives (Phase 10A).

Pure functions only - no database access here (see app.services.auth_service
for the DB-touching user creation/authentication logic that calls into
this module). Kept separate so the cryptographic building blocks are easy
to audit and test in isolation from ORM/session concerns.

Password hashing: Argon2id via argon2-cffi, used directly (not through
passlib, which has been effectively unmaintained for several years).
Argon2id is the OWASP-recommended default for new applications and is
fully compatible with this project's Python 3.10 stack.

JWT: PyJWT, HS256 by default (symmetric - the same JWT_SECRET_KEY signs
and verifies). The secret always comes from Settings (backend/.env /
JWT_SECRET_KEY), never hardcoded here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

from app.core.config import get_settings

# A single, module-level PasswordHasher using argon2-cffi's defaults, which
# already match OWASP's current recommended Argon2id parameters (m=19 MiB,
# t=2, p=1 as of argon2-cffi 23.x). The encoded hash string this produces
# embeds the algorithm and parameters used, so those can change in a later
# release without invalidating already-stored hashes or needing a migration.
_password_hasher = PasswordHasher()

JWT_TOKEN_TYPE = "access"  # the only token type this phase issues


class TokenError(Enum):
    """Why decode_access_token() rejected a token - lets callers (see
    app.api.deps.get_current_user) return a precise, correct 401 without
    string-matching exception messages."""

    MISSING = "missing"
    MALFORMED = "malformed"
    EXPIRED = "expired"
    INVALID = "invalid"


class InvalidTokenException(Exception):
    """Raised by decode_access_token() for any token that isn't a live,
    correctly-signed, correctly-shaped access token. Carries a TokenError
    so the caller can pick the right error message without inspecting
    exception text."""

    def __init__(self, reason: TokenError):
        self.reason = reason
        super().__init__(reason.value)


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id. Returns the full encoded
    hash string (algorithm + parameters + salt + hash) - store this whole
    string as User.password_hash; never store the plaintext."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True if `password` matches the given Argon2id hash. Never raises
    for a wrong password or a malformed/foreign hash - both simply return
    False, which is what every caller actually wants (a login attempt).
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------


def create_access_token(*, user_id: uuid.UUID, email: str) -> str:
    """Create a signed JWT access token.

    Claims:
    - sub: the user's id (str, per JWT convention - "sub" must be a string)
    - email: for convenience (never anything more sensitive)
    - type: "access" - lets a later phase distinguish token kinds
      (e.g. a refresh token) without changing this token's own shape
    - iat / exp: issued-at and expiration, both required for a real
      expiration check to mean anything

    Never includes the password or password_hash.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": JWT_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str | None) -> dict:
    """Validate and decode a JWT access token, or raise
    InvalidTokenException with a specific TokenError reason.

    Checks (in order): present, well-formed and correctly signed, not
    expired, and of type "access" - a token that is technically valid JWT
    but not one this function issued (wrong type) is treated as invalid
    rather than silently accepted.
    """
    if not token:
        raise InvalidTokenException(TokenError.MISSING)

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenException(TokenError.EXPIRED) from exc
    except jwt.InvalidTokenError as exc:
        # Covers malformed tokens, bad signatures, missing required
        # claims, wrong algorithm, etc. - anything not specifically
        # "expired" from PyJWT's own exception hierarchy.
        raise InvalidTokenException(TokenError.MALFORMED) from exc

    if payload.get("type") != JWT_TOKEN_TYPE:
        raise InvalidTokenException(TokenError.INVALID)

    return payload
