"""Authenticated analysis-history endpoints (Phase 11).

Read-only: GET /api/analyses (paginated list) and
GET /api/analyses/{analysis_id} (full detail). Neither ever calls
app.services.resume_matcher.match_resume_to_job or
app.services.semantic_matcher.compute_semantic_match - every field
returned comes from what save_analysis_result already persisted (Phase
9C-3), reconstructed via analysis_repository.load_analysis_for_user, plus
the already-persisted Resume/JobDescription rows.

Ownership is always derived from current_user (the verified JWT
subject), never from a client-supplied user_id - mirrors resume.py /
job_description.py. A nonexistent analysis_id and one that exists but
belongs to another user return the identical 404, so a caller can't
distinguish the two by probing (same policy used throughout Phase 10B).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.analysis import (
    AnalysisDetailResponse,
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisRecommendations,
)
from app.services.analysis_repository import list_analyses_for_user, load_analysis_for_user
from app.services.job_description_repository import load_parsed_job_description
from app.services.resume_repository import load_parsed_resume

router = APIRouter(prefix="/analyses", tags=["analyses"])

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisListResponse:
    rows, total = list_analyses_for_user(db, user_id=current_user.id, page=page, page_size=page_size)
    items = [
        AnalysisListItem(
            analysis_id=row.id,
            resume_id=row.resume_id,
            job_description_id=row.job_description_id,
            deterministic_score=row.deterministic_score,
            semantic_score=row.semantic_score,
            combined_score=row.combined_score,
            created_at=row.created_at,
        )
        for row in rows
    ]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return AnalysisListResponse(items=items, page=page, page_size=page_size, total=total, total_pages=total_pages)


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis_detail(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisDetailResponse:
    persisted = load_analysis_for_user(db, analysis_id, user_id=current_user.id)
    if persisted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found with id {analysis_id}.",
        )

    # persisted's existence already proves (via load_analysis_for_user's
    # ownership check) that its resume_id/job_description_id belong to
    # current_user - these reads are ownership-blind on purpose, exactly
    # like every other id-based lookup once ownership of the parent
    # analysis has already been established.
    resume = load_parsed_resume(db, persisted.resume_id)
    job_description = load_parsed_job_description(db, persisted.job_description_id)
    if resume is None or job_description is None:
        # Not reachable in practice - ON DELETE CASCADE means an analysis
        # cannot outlive its resume/job description - but keeps this
        # endpoint honest about its own types rather than asserting.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="This analysis is missing its underlying resume or job description data.",
        )

    settings = get_settings()
    recommendations = persisted.recommendations if isinstance(persisted.recommendations, dict) else {}

    return AnalysisDetailResponse(
        analysis_id=persisted.analysis_id,
        resume_id=persisted.resume_id,
        job_description_id=persisted.job_description_id,
        created_at=persisted.created_at,
        deterministic_score=persisted.deterministic_score,
        semantic_score=persisted.semantic_score,
        combined_score=persisted.combined_score,
        semantic_matches=persisted.semantic_matches,
        semantic_model_name=settings.semantic_model_name,
        semantic_similarity_threshold=settings.semantic_similarity_threshold,
        summary=persisted.summary,
        recommendations=AnalysisRecommendations(
            missing_required_skills=recommendations.get("missing_required_skills", []),
            missing_preferred_skills=recommendations.get("missing_preferred_skills", []),
            missing_certifications=recommendations.get("missing_certifications", []),
            missing_languages=recommendations.get("missing_languages", []),
        ),
        resume=resume,
        job_description=job_description,
    )
