"""ORM models (Phase 9B).

Importing this package (or any of its submodules) registers every table on
app.core.database.Base.metadata. This module must be imported - directly
or transitively - before Alembic's autogenerate reads that metadata, and
before any code calls Base.metadata.create_all() (which Phase 9B does not
do; Alembic migrations are the source of truth for schema changes).
"""

from app.models.analysis import AnalysisSkillResult, AnalysisSummary, ResumeAnalysis
from app.models.job_description import JobDescription, JobRequirement
from app.models.resume import (
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeLanguage,
    ResumeProject,
    ResumeSkill,
)

__all__ = [
    "AnalysisSkillResult",
    "AnalysisSummary",
    "JobDescription",
    "JobRequirement",
    "Resume",
    "ResumeAnalysis",
    "ResumeCertification",
    "ResumeEducation",
    "ResumeExperience",
    "ResumeLanguage",
    "ResumeProject",
    "ResumeSkill",
]
