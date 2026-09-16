"""Phase 9B: coverage for the ORM models and the DB-level guarantees their
migration created (cascades, unique constraints, check constraints).

These tests use the real PostgreSQL database (there is no in-memory
substitute for PostgreSQL-specific behavior like ON DELETE CASCADE, native
UUID, or CHECK constraints). Every test runs inside an outer transaction
that is always rolled back, via the SAVEPOINT-based pattern SQLAlchemy
recommends for test isolation, so nothing written here is ever persisted.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models import (
    AnalysisSummary,
    JobDescription,
    JobRequirement,
    Resume,
    ResumeAnalysis,
    ResumeEducation,
    ResumeSkill,
)


def test_all_twelve_tables_registered():
    expected = {
        "resumes", "resume_skills", "resume_education", "resume_experience",
        "resume_projects", "resume_certifications", "resume_languages",
        "job_descriptions", "job_requirements", "resume_analyses",
        "analysis_skill_results", "analysis_summaries",
    }
    assert expected <= set(Base.metadata.tables.keys())


def test_resume_skill_unique_constraint_rejects_duplicate(db_session):
    resume = Resume(original_filename="a.pdf", extracted_text="text")
    db_session.add(resume)
    db_session.flush()

    db_session.add(ResumeSkill(resume_id=resume.id, skill="Python"))
    db_session.flush()
    db_session.add(ResumeSkill(resume_id=resume.id, skill="Python"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_resume_skill_check_constraint_rejects_invalid_source(db_session):
    resume = Resume(original_filename="a.pdf", extracted_text="text")
    db_session.add(resume)
    db_session.flush()

    db_session.add(ResumeSkill(resume_id=resume.id, skill="Python", source="not_a_valid_source"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_job_requirement_check_constraint_rejects_invalid_category(db_session):
    jd = JobDescription(raw_text="We need a developer.")
    db_session.add(jd)
    db_session.flush()

    db_session.add(
        JobRequirement(job_description_id=jd.id, requirement="Python", category="not_a_real_category")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cascade_delete_removes_child_rows(db_session):
    resume = Resume(original_filename="a.pdf", extracted_text="text")
    resume.skills.append(ResumeSkill(skill="Python"))
    resume.education.append(ResumeEducation(institution="MIT"))
    db_session.add(resume)
    db_session.flush()
    resume_id = resume.id

    db_session.delete(resume)
    db_session.flush()

    remaining_skills = (
        db_session.query(ResumeSkill).filter_by(resume_id=resume_id).count()
    )
    remaining_education = (
        db_session.query(ResumeEducation).filter_by(resume_id=resume_id).count()
    )
    assert remaining_skills == 0
    assert remaining_education == 0


def test_analysis_summary_is_one_to_one(db_session):
    resume = Resume(original_filename="a.pdf", extracted_text="text")
    jd = JobDescription(raw_text="We need a developer.")
    db_session.add_all([resume, jd])
    db_session.flush()

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        job_description_id=jd.id,
        deterministic_score=80.0,
        semantic_score=70.0,
        combined_score=77.0,
    )
    db_session.add(analysis)
    db_session.flush()

    db_session.add(AnalysisSummary(analysis_id=analysis.id, summary_text="Good match."))
    db_session.flush()

    # A second summary for the same analysis must violate the unique
    # constraint that enforces "one summary per analysis" at the DB level.
    db_session.add(AnalysisSummary(analysis_id=analysis.id, summary_text="Another summary."))
    with pytest.raises(IntegrityError):
        db_session.flush()
