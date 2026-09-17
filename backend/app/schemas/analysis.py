"""Analysis-history response schemas (Phase 11).

Dedicated Pydantic models for GET /api/analyses and
GET /api/analyses/{analysis_id} - routers never return raw SQLAlchemy
ORM objects. Every field here is read from what save_analysis_result
already persisted (Phase 9C-3) plus the already-persisted Resume/
JobDescription rows; nothing here is computed by re-running the
deterministic/semantic matcher.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.job_description import ParsedJobDescription
from app.schemas.match import SemanticMatchItem
from app.schemas.resume import ParsedResume


class AnalysisListItem(BaseModel):
    """One row of a user's analysis history (GET /api/analyses)."""

    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID
    deterministic_score: float
    semantic_score: float
    combined_score: float
    created_at: datetime


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class AnalysisRecommendations(BaseModel):
    """The deterministic matcher's own already-computed "missing" lists,
    exactly as save_analysis_result persisted them onto
    AnalysisSummary.recommendations_json - not a new recommendation
    feature and not recomputed here."""

    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    missing_certifications: list[str] = Field(default_factory=list)
    missing_languages: list[str] = Field(default_factory=list)


class AnalysisDetailResponse(BaseModel):
    """Full persisted analysis (GET /api/analyses/{analysis_id}).

    semantic_model_name / semantic_similarity_threshold are the app's
    current configuration values (app.core.config.Settings), included for
    display context alongside semantic_matches - not a recomputation of
    any match result. combined_score_formula mirrors
    app.schemas.match.ResumeMatchResponse's own fixed description string.
    """

    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID
    created_at: datetime

    deterministic_score: float
    semantic_score: float
    combined_score: float
    combined_score_formula: str = (
        "combined_match_score = 0.7 * deterministic_match.score + 0.3 * semantic_match.semantic_score"
    )

    semantic_matches: list[SemanticMatchItem] = Field(default_factory=list)
    semantic_model_name: str
    semantic_similarity_threshold: float

    summary: str
    recommendations: AnalysisRecommendations

    resume: ParsedResume
    job_description: ParsedJobDescription
