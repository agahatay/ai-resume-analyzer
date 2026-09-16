"""User ORM model (Phase 10A).

Owns Resume and JobDescription rows going forward (see the user_id FK
added to those models in this same phase). ResumeAnalysis deliberately
gets no user_id of its own - its ownership is derivable through
analysis.resume.user_id (or analysis.job_description.user_id), so adding
a third, redundant copy of the same fact would just be another place for
it to drift out of sync.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job_description import JobDescription
    from app.models.resume import Resume


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered account. Never serialize password_hash - see
    app.schemas.auth.UserResponse, which deliberately omits it."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    # An Argon2id encoded hash string (algorithm + parameters + salt + hash,
    # all self-contained - see app/core/security.py) - never the plaintext
    # password. Typically ~95-100 chars; 255 leaves generous headroom for
    # future parameter changes without a migration.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    resumes: Mapped[list["Resume"]] = relationship(back_populates="owner")
    job_descriptions: Mapped[list["JobDescription"]] = relationship(back_populates="owner")
