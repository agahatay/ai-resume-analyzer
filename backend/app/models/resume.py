"""Resume ORM models (Phase 9B).

These map the already-extracted, structured representation of a resume -
never the original PDF bytes. Text extraction happens upstream in
app.services.pdf_service; nothing here changes that pipeline.
"""

from __future__ import annotations

import uuid
from datetime import date as dt_date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Date as SQLDate
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A parsed resume: extracted text plus structured contact fields."""

    __tablename__ = "resumes"

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Indexed: candidate email is the most likely lookup key for "find this
    # person's past resumes/analyses" in a future phase.
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # order_by=<pk> on every child collection below (Phase 9C-1): without it,
    # PostgreSQL does not guarantee row order for a plain SELECT, which would
    # make resume reconstruction (see resume_repository.load_parsed_resume)
    # non-deterministic. This is a query-ordering hint only - no column,
    # table, or migration change.
    skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ResumeSkill.id"
    )
    education: Mapped[list["ResumeEducation"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ResumeEducation.id"
    )
    work_experience: Mapped[list["ResumeExperience"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ResumeExperience.id"
    )
    projects: Mapped[list["ResumeProject"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ResumeProject.id"
    )
    certifications: Mapped[list["ResumeCertification"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ResumeCertification.id",
    )
    languages: Mapped[list["ResumeLanguage"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ResumeLanguage.id"
    )
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True
    )


class ResumeSkill(CreatedAtMixin, Base):
    """One skill extracted from (or manually attached to) a resume."""

    __tablename__ = "resume_skills"
    __table_args__ = (
        # Prevents the same skill being stored twice for one resume (avoids
        # duplicate derived data). Because this composite index leads with
        # resume_id, it also covers "all skills for resume X" lookups, so a
        # separate single-column index on resume_id would be redundant.
        UniqueConstraint("resume_id", "skill", name="uq_resume_skills_resume_id_skill"),
        CheckConstraint("source in ('parsed', 'manual')", name="ck_resume_skills_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    skill: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="parsed")

    resume: Mapped["Resume"] = relationship(back_populates="skills")


class ResumeEducation(Base):
    """One education entry belonging to a resume."""

    __tablename__ = "resume_education"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[dt_date | None] = mapped_column(SQLDate, nullable=True)
    end_date: Mapped[dt_date | None] = mapped_column(SQLDate, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="education")


class ResumeExperience(Base):
    """One work-experience entry belonging to a resume."""

    __tablename__ = "resume_experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[dt_date | None] = mapped_column(SQLDate, nullable=True)
    end_date: Mapped[dt_date | None] = mapped_column(SQLDate, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="work_experience")


class ResumeProject(Base):
    """One project entry belonging to a resume."""

    __tablename__ = "resume_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-text (e.g. "Python, FastAPI, PostgreSQL") rather than JSON/a join
    # table: it's a single denormalized blurb tied to one project row, not
    # an entity that needs independent querying the way ResumeSkill does.
    technologies: Mapped[str | None] = mapped_column(Text, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="projects")


class ResumeCertification(Base):
    """One certification entry belonging to a resume."""

    __tablename__ = "resume_certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[dt_date | None] = mapped_column(SQLDate, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="certifications")


class ResumeLanguage(Base):
    """One spoken/written language entry belonging to a resume."""

    __tablename__ = "resume_languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="languages")
