"""Shared FastAPI dependencies (Phase 10A).

get_current_user is the one dependency Phase 10A introduces. It is not
wired into any resume/job-description/match endpoint yet - only into
GET /api/auth/me - per this phase's explicit scope. Phase 10B will import
it from here to protect the rest of the API.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenException, TokenError, decode_access_token
from app.models.user import User
from app.services.auth_service import get_user_by_id

# auto_error=False: a missing/wrong-scheme Authorization header should
# reach our own code as "no token" so we can raise a 401 (this phase's
# required behavior) instead of HTTPBearer's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)

_TOKEN_ERROR_DETAIL: dict[TokenError, str] = {
    TokenError.MISSING: "Not authenticated.",
    TokenError.MALFORMED: "Invalid authentication token.",
    TokenError.EXPIRED: "Authentication token has expired.",
    TokenError.INVALID: "Invalid authentication token.",
}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated User from an `Authorization: Bearer
    <token>` header, or raise 401.

    Order of checks: token present -> well-formed and correctly signed ->
    not expired -> references a real user -> that user is active. Any
    failure raises the same 401 status (with a specific, non-leaky detail
    message) so callers get a uniform "not authenticated" contract.
    """
    token = credentials.credentials if credentials is not None else None

    try:
        payload = decode_access_token(token)
    except InvalidTokenException as exc:
        raise _unauthorized(_TOKEN_ERROR_DETAIL[exc.reason]) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise _unauthorized("Invalid authentication token.") from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("User not found.")
    if not user.is_active:
        raise _unauthorized("This account has been deactivated.")

    return user
