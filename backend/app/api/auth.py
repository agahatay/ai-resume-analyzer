"""Authentication endpoints (Phase 10A).

Only these three routes exist so far: register, login, and a protected
/me used to prove the whole chain (hash -> store -> login -> JWT ->
verify -> load user) works end to end. No other endpoint in this app
requires a token yet - see app/api/deps.get_current_user's docstring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    try:
        user = create_user(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user.",
        ) from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    settings = get_settings()
    access_token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=access_token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
