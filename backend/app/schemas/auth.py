"""Auth request/response schemas (Phase 10A)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 200


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_must_not_be_only_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("password must not be blank or whitespace only")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserResponse(BaseModel):
    """Safe, public view of a User. Deliberately has no password_hash
    field at all - not even one that's excluded at serialization time -
    so there is no field here that could ever be accidentally returned.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Seconds until the token expires, for client convenience - derived
    # from the same Settings.access_token_expire_minutes used to actually
    # sign the token, not a separately-maintained value.
    expires_in: int
