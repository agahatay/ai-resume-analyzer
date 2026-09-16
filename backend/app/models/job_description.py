"""Job description ORM models (Phase 9B)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis

# Mirrors app.schemas.job_description.ParsedJobDescription's category buckets
# (required_skills / preferred_skills / education / experience /
# certifications / languages), singularized to name one requirement's type.
JOB_REQUIREMENT_CATEGORIES = (
    "required_skill",
    "preferred_skill",
    "education",
    "experience",
    "certification",
    "language",
)


class JobDescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A job description: raw text plus an optional parsed title."""

    __tablename__ = "job_descriptions"

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan", passive_deletes=True
    )


class JobRequirement(CreatedAtMixin, Base):
    """One individual requirement parsed out of a job description."""

    __tablename__ = "job_requirements"
    __table_args__ = (
        CheckConstraint(
            "category in (" + ", ".join(f"'{c}'" for c in JOB_REQUIREMENT_CATEGORIES) + ")",
            name="ck_job_requirements_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement: Mapped[str] = mapped_column(String(500), nullable=False)
    # e.g. required_skill / preferred_skill / education / experience /
    # certification / language - see JOB_REQUIREMENT_CATEGORIES above.
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    job_description: Mapped["JobDescription"] = relationship(back_populates="requirements")
