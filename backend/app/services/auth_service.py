"""User authentication service (Phase 10A).

The DB-touching counterpart to app.core.security's pure crypto/JWT
functions. Mirrors the shape of resume_repository.py /
job_description_repository.py: routers stay thin and translate the
handful of raised exceptions here into HTTP responses.

Responsibilities:
- create_user (register)
- authenticate_user (login)
- get_user_by_id / get_user_by_email

JWT creation itself lives in app.core.security.create_access_token; this
module calls it but doesn't duplicate its logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    """Raised by create_user() when the email is already taken."""


class InvalidCredentialsError(Exception):
    """Raised by authenticate_user() for a wrong email or password.

    Deliberately the same exception (and the same HTTP response, at the
    router level) for both cases - an attacker probing which emails are
    registered must not be able to tell "no such user" apart from "wrong
    password" from the response alone.
    """


class InactiveUserError(Exception):
    """Raised by authenticate_user() when the account exists, the
    password is correct, but the user has been deactivated."""


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, *, email: str, password: str, full_name: str | None = None) -> User:
    """Register a new user. Raises EmailAlreadyRegisteredError if the
    email is already taken. The plaintext password never gets stored -
    only its Argon2id hash does."""
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(f"A user with email {email!r} is already registered.")

    user = User(email=email, password_hash=hash_password(password), full_name=full_name)
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    """Verify credentials and return the matching, active User.

    Raises InvalidCredentialsError for a wrong email or password (see
    that exception's docstring for why both cases look identical from the
    caller's side), or InactiveUserError if the account is deactivated.
    """
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password.")
    if not user.is_active:
        raise InactiveUserError("This account has been deactivated.")
    return user
