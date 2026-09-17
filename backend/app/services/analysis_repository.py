"""Analysis persistence layer (Phase 9C-3).

Mirrors the design of resume_repository.py / job_description_repository.py
(Phase 9C-1/9C-2): this is the only module that should issue SQLAlchemy
writes for resume-analysis results. Routers stay thin. Nothing here
touches the deterministic or semantic matching formulas
(app.services.resume_matcher / semantic_matcher) - it only persists and
reconstructs the ResumeMatchResponse those already produce.

Responsibilities:
- create_analysis / get_analysis
- save_analysis_result (persist one full match result in one transaction)
- load_analysis (reconstruct a persisted analysis without rerunning the
  matcher)
- list_analyses_for_resume / list_analyses_for_job_description (history,
  newest first)

Unlike resume/job-description persistence, this layer is intentionally
append-only: save_analysis_result always creates a brand new
ResumeAnalysis row rather than updating an existing one, so analysis
history is preserved across repeated matches of the same
resume+job description pair.

Transaction handling: save_analysis_result performs exactly one
transaction for the ResumeAnalysis row and all of its child rows
(AnalysisSkillResult, AnalysisSummary) together - commit on success,
rollback on any exception, so a caller never observes (or leaves behind)
a half-written analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import AnalysisSkillResult, AnalysisSummary, ResumeAnalysis
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.schemas.match import ResumeMatchResponse, SemanticMatchItem


class PersistedAnalysisResult(BaseModel):
    """What load_analysis() reconstructs from PostgreSQL.

    This is deliberately not the full ResumeMatchResponse: fields like
    per-dimension education/experience status text are never persisted
    (only the three numeric scores are - see ResumeAnalysis), so
    reconstructing a full ResumeMatchResponse from the database alone
    isn't possible without re-running the matcher, which load_analysis
    must not do. This shape contains exactly what Phase 9C-3 requires:
    the three scores, the semantic match items, the summary, and the
    recommendations - all read from stored rows.
    """

    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID
    deterministic_score: float
    semantic_score: float
    combined_score: float
    semantic_matches: list[SemanticMatchItem] = Field(default_factory=list)
    summary: str
    recommendations: Any | None = None
    created_at: datetime


# --------------------------------------------------------------------------
# Basic CRUD
# --------------------------------------------------------------------------


def create_analysis(
    db: Session,
    *,
    resume_id: uuid.UUID,
    job_description_id: uuid.UUID,
    deterministic_score: float,
    semantic_score: float,
    combined_score: float,
) -> ResumeAnalysis:
    """Create and persist a bare ResumeAnalysis row (no child rows).

    Most callers want save_analysis_result instead, which also persists
    the semantic skill results and summary in the same transaction. This
    lower-level primitive exists for the cases (and tests) that only need
    the scores row itself.
    """
    analysis = ResumeAnalysis(
        resume_id=resume_id,
        job_description_id=job_description_id,
        deterministic_score=deterministic_score,
        semantic_score=semantic_score,
        combined_score=combined_score,
    )
    db.add(analysis)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis


def get_analysis(db: Session, analysis_id: uuid.UUID) -> ResumeAnalysis | None:
    """Fetch a ResumeAnalysis by id, or None if it does not exist.
    Ownership-blind on purpose - see get_analysis_for_user for the
    ownership-checked equivalent, which any HTTP-facing caller should
    use instead."""
    return db.get(ResumeAnalysis, analysis_id)


def get_analysis_for_user(db: Session, analysis_id: uuid.UUID, *, user_id: uuid.UUID) -> ResumeAnalysis | None:
    """Fetch a ResumeAnalysis by id, but only if it belongs to user_id -
    returns None both when the analysis doesn't exist and when it exists
    but belongs to someone else (the same "don't distinguish" policy used
    throughout Phase 10B; see resume_repository.get_or_create_resume_for_parse).

    Per this phase's requirement, ResumeAnalysis has no user_id column of
    its own; ownership is derived through analysis.resume.user_id.
    """
    analysis = db.get(ResumeAnalysis, analysis_id, options=[selectinload(ResumeAnalysis.resume)])
    if analysis is None or analysis.resume.user_id != user_id:
        return None
    return analysis


# --------------------------------------------------------------------------
# Saving a full match result
# --------------------------------------------------------------------------


def save_analysis_result(
    db: Session,
    *,
    resume_id: uuid.UUID,
    job_description_id: uuid.UUID,
    match_result: ResumeMatchResponse,
) -> ResumeAnalysis:
    """Persist one complete match result as a new ResumeAnalysis, with its
    semantic skill results and summary, in a single transaction.

    Scores are copied verbatim from match_result - deterministic_score
    from match_result.deterministic_match.score, semantic_score from
    match_result.semantic_match.semantic_score, combined_score from
    match_result.combined_match_score. Nothing is recalculated here.

    AnalysisSkillResult rows come from match_result.semantic_match's
    per-requirement items (the only per-item list already shaped as
    requirement/category/similarity/matched - the deterministic side only
    produces aggregate flat lists, not one row's worth of columns per
    item; see the Phase 9C-3 report for this design choice).

    AnalysisSummary.recommendations_json is a structured copy of the
    matcher's own already-computed "missing" lists (missing required/
    preferred skills, missing certifications, missing languages) - not a
    new recommendation-generation feature, and not a recalculation of
    anything: every value in it is read directly off match_result.

    Every call creates a brand new ResumeAnalysis row; this function never
    updates or replaces a prior analysis (see module docstring).
    """
    try:
        analysis = ResumeAnalysis(
            resume_id=resume_id,
            job_description_id=job_description_id,
            deterministic_score=match_result.deterministic_match.score,
            semantic_score=match_result.semantic_match.semantic_score,
            combined_score=match_result.combined_match_score,
        )
        db.add(analysis)
        db.flush()  # assigns analysis.id, needed by the child rows below

        skill_result_rows = [
            AnalysisSkillResult(
                analysis_id=analysis.id,
                requirement=item.requirement,
                matched_resume_skill=item.matched_resume_text,
                similarity=item.similarity,
                matched=item.matched,
                category=item.category,
            )
            for item in match_result.semantic_match.semantic_matches
        ]
        if skill_result_rows:
            db.add_all(skill_result_rows)

        recommendations_json = {
            "missing_required_skills": match_result.missing_required_skills,
            "missing_preferred_skills": match_result.missing_preferred_skills,
            "missing_certifications": match_result.certification_match.missing,
            "missing_languages": match_result.language_match.missing,
        }
        db.add(
            AnalysisSummary(
                analysis_id=analysis.id,
                summary_text=match_result.summary,
                recommendations_json=recommendations_json,
            )
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis


# --------------------------------------------------------------------------
# Reconstruction (no re-matching)
# --------------------------------------------------------------------------


def load_analysis(db: Session, analysis_id: uuid.UUID) -> PersistedAnalysisResult | None:
    """Reconstruct a persisted analysis from PostgreSQL, or None if it
    doesn't exist. Reads stored rows only - never calls match_resume_to_job
    or compute_semantic_match."""
    analysis = db.get(
        ResumeAnalysis,
        analysis_id,
        options=[selectinload(ResumeAnalysis.skill_results), selectinload(ResumeAnalysis.summary)],
    )
    if analysis is None:
        return None

    semantic_matches = [
        SemanticMatchItem(
            category=row.category,
            requirement=row.requirement,
            matched_resume_text=row.matched_resume_skill,
            # similarity is nullable at the schema level for generality, but
            # save_analysis_result always populates it from a required
            # SemanticMatchItem.similarity float; default to 0.0 defensively
            # for any row written some other way.
            similarity=row.similarity if row.similarity is not None else 0.0,
            matched=row.matched,
        )
        for row in analysis.skill_results
    ]

    summary_text = analysis.summary.summary_text if analysis.summary is not None else ""
    recommendations = analysis.summary.recommendations_json if analysis.summary is not None else None

    return PersistedAnalysisResult(
        analysis_id=analysis.id,
        resume_id=analysis.resume_id,
        job_description_id=analysis.job_description_id,
        deterministic_score=analysis.deterministic_score,
        semantic_score=analysis.semantic_score,
        combined_score=analysis.combined_score,
        semantic_matches=semantic_matches,
        summary=summary_text,
        recommendations=recommendations,
        created_at=analysis.created_at,
    )


def load_analysis_for_user(
    db: Session, analysis_id: uuid.UUID, *, user_id: uuid.UUID
) -> PersistedAnalysisResult | None:
    """Ownership-checked load_analysis: None if the analysis doesn't
    exist or isn't owned (via its Resume) by user_id."""
    if get_analysis_for_user(db, analysis_id, user_id=user_id) is None:
        return None
    return load_analysis(db, analysis_id)


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------


def list_analyses_for_resume(db: Session, resume_id: uuid.UUID, *, user_id: uuid.UUID) -> list[ResumeAnalysis]:
    """All analyses for a resume, newest first - but only if that resume
    is owned by user_id. Otherwise an empty list, exactly as if no
    analyses existed, so a caller can never learn anything about a
    resume_id it doesn't own (including whether it exists at all) just
    by requesting its history.
    """
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        return []
    return (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.resume_id == resume_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )


def list_analyses_for_job_description(
    db: Session, job_description_id: uuid.UUID, *, user_id: uuid.UUID
) -> list[ResumeAnalysis]:
    """All analyses for a job description, newest first - ownership-gated
    the same way as list_analyses_for_resume, above."""
    job_description = db.get(JobDescription, job_description_id)
    if job_description is None or job_description.user_id != user_id:
        return []
    return (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.job_description_id == job_description_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )


def list_analyses_for_user(
    db: Session, *, user_id: uuid.UUID, page: int = 1, page_size: int = 10
) -> tuple[list[ResumeAnalysis], int]:
    """A user's full analysis history (Phase 11) - across every resume
    and job description they own, newest first, paginated.

    Ownership is enforced at the database query level: the join to Resume
    and the ``Resume.user_id == user_id`` filter both happen in the SQL
    itself, not via a Python-side post-filter, so a caller can never see
    another user's analyses by paging past their own. (ResumeAnalysis has
    no user_id column of its own - see get_analysis_for_user's docstring
    - so Resume is the only table that can carry that filter.)

    Returns (page_of_analyses, total_count) - total_count is the full
    count across all pages, for the caller to compute total_pages.
    """
    base_query = db.query(ResumeAnalysis).join(Resume, ResumeAnalysis.resume_id == Resume.id).filter(
        Resume.user_id == user_id
    )
    total = base_query.count()
    items = (
        base_query.order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
