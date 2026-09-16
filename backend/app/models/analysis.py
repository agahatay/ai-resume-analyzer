"""Resume-analysis ORM models (Phase 9B).

These map the result of matching one resume against one job description
(see app.services.resume_matcher / semantic_matcher) - not the matching
algorithms themselves, which are untouched by this phase.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.job_description import JobDescription
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.resume import Resume

# Mirrors app.schemas.match.SemanticMatchItem.category's Literal values.
ANALYSIS_SKILL_RESULT_CATEGORIES = (
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
)


class ResumeAnalysis(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One match run of a specific resume against a specific job
    description, storing the deterministic/semantic/combined scores."""

    __tablename__ = "resume_analyses"
    __table_args__ = (
        # Leads with resume_id, so it also covers "all analyses for this
        # resume" lookups - a separate single-column index on resume_id
        # would be redundant with this one.
        Index("ix_resume_analyses_resume_id_job_description_id", "resume_id", "job_description_id"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deterministic_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    combined_score: Mapped[float] = mapped_column(Float, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="analyses")
    job_description: Mapped["JobDescription"] = relationship(back_populates="analyses")
    # order_by=<pk> (Phase 9C-3): without it, PostgreSQL does not guarantee
    # row order for a plain SELECT, which would make analysis reconstruction
    # (see analysis_repository.load_analysis) non-deterministic. Same
    # query-ordering-hint-only fix applied to Resume/JobDescription's child
    # relationships in Phase 9C-1/9C-2 - no column/table/migration change.
    skill_results: Mapped[list["AnalysisSkillResult"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AnalysisSkillResult.id",
    )
    summary: Mapped["AnalysisSummary | None"] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class AnalysisSkillResult(Base):
    """One per-requirement match result within a ResumeAnalysis (mirrors
    app.schemas.match.SemanticMatchItem)."""

    __tablename__ = "analysis_skill_results"
    __table_args__ = (
        CheckConstraint(
            "category in (" + ", ".join(f"'{c}'" for c in ANALYSIS_SKILL_RESULT_CATEGORIES) + ")",
            name="ck_analysis_skill_results_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resume_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement: Mapped[str] = mapped_column(String(500), nullable=False)
    matched_resume_skill: Mapped[str | None] = mapped_column(String(255), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    analysis: Mapped["ResumeAnalysis"] = relationship(back_populates="skill_results")


class AnalysisSummary(Base):
    """The one-to-one human-readable summary + recommendations for a
    ResumeAnalysis. analysis_id is unique to enforce the 1:1 relationship
    at the database level, not just in the ORM."""

    __tablename__ = "analysis_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resume_analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    # The only JSON/JSONB column in the schema: recommendations are a
    # variable-shape list of structured items with no independent identity
    # of their own, so a join table would add normalization without adding
    # any real query capability.
    recommendations_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)

    analysis: Mapped["ResumeAnalysis"] = relationship(back_populates="summary")
