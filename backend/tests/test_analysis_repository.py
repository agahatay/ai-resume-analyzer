"""Phase 9C-3: integration tests for app.services.analysis_repository.

Mirrors tests/test_resume_repository.py and
tests/test_job_description_repository.py's approach: these exercise the
repository directly against the real PostgreSQL database inside the
db_session fixture's SAVEPOINT-based transaction, which is always rolled
back at teardown, so nothing here is ever actually persisted.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.analysis import AnalysisSkillResult, AnalysisSummary, ResumeAnalysis
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.schemas.match import (
    CertificationMatchResult,
    DeterministicMatchSummary,
    EducationMatchResult,
    ExperienceMatchResult,
    LanguageMatchResult,
    ResumeMatchResponse,
    SemanticMatchItem,
    SemanticMatchResult,
)
from app.services import analysis_repository


def _make_match_response(**overrides) -> ResumeMatchResponse:
    education_match = EducationMatchResult(status="matched", details="Meets the requirement.")
    experience_match = ExperienceMatchResult(
        status="matched", details="Meets the requirement.", required_years=3.0, resume_years=5.0
    )
    certification_match = CertificationMatchResult(matched=["AWS Certified"], missing=["PMP"])
    language_match = LanguageMatchResult(matched=["English"], missing=["German"])

    deterministic_match = DeterministicMatchSummary(
        score=85.0,
        matched_skills=["Python"],
        missing_required_skills=["Go"],
        matched_preferred_skills=["Docker"],
        missing_preferred_skills=["Kubernetes"],
        education_match=education_match,
        experience_match=experience_match,
        certification_match=certification_match,
        language_match=language_match,
    )
    semantic_match = SemanticMatchResult(
        semantic_score=72.5,
        semantic_matches=[
            SemanticMatchItem(
                category="skills", requirement="Python", matched_resume_text="Python", similarity=0.95, matched=True
            ),
            SemanticMatchItem(
                category="education",
                requirement="Bachelor's degree",
                matched_resume_text=None,
                similarity=0.1,
                matched=False,
            ),
        ],
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold=0.3,
    )
    defaults = dict(
        overall_match_score=85.0,
        matched_skills=["Python"],
        missing_required_skills=["Go"],
        matched_preferred_skills=["Docker"],
        missing_preferred_skills=["Kubernetes"],
        education_match=education_match,
        experience_match=experience_match,
        certification_match=certification_match,
        language_match=language_match,
        summary="Strong match overall.",
        deterministic_match=deterministic_match,
        semantic_match=semantic_match,
        combined_match_score=81.25,
    )
    defaults.update(overrides)
    return ResumeMatchResponse(**defaults)


def _make_resume_and_jd(db_session) -> tuple[Resume, JobDescription]:
    resume = Resume(original_filename="a.pdf", extracted_text="resume text")
    jd = JobDescription(raw_text="jd text")
    db_session.add_all([resume, jd])
    db_session.flush()
    return resume, jd


# --------------------------------------------------------------------------
# 1 & 2: create_analysis / scores
# --------------------------------------------------------------------------


def test_create_analysis_persists_row_and_scores(db_session):
    resume, jd = _make_resume_and_jd(db_session)

    analysis = analysis_repository.create_analysis(
        db_session,
        resume_id=resume.id,
        job_description_id=jd.id,
        deterministic_score=80.0,
        semantic_score=70.0,
        combined_score=77.0,
    )
    assert analysis.id is not None
    assert analysis.created_at is not None

    fetched = db_session.get(ResumeAnalysis, analysis.id)
    assert fetched.resume_id == resume.id
    assert fetched.job_description_id == jd.id
    assert fetched.deterministic_score == 80.0
    assert fetched.semantic_score == 70.0
    assert fetched.combined_score == 77.0


def test_get_analysis_returns_none_for_unknown_id(db_session):
    assert analysis_repository.get_analysis(db_session, uuid.uuid4()) is None


def test_save_analysis_result_uses_exact_scores_from_match_result(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    fetched = db_session.get(ResumeAnalysis, analysis.id)
    assert fetched.deterministic_score == match_result.deterministic_match.score
    assert fetched.semantic_score == match_result.semantic_match.semantic_score
    assert fetched.combined_score == match_result.combined_match_score


# --------------------------------------------------------------------------
# 3 & 4: semantic skill results + categories
# --------------------------------------------------------------------------


def test_save_analysis_result_persists_skill_results(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    rows = (
        db_session.query(AnalysisSkillResult)
        .filter_by(analysis_id=analysis.id)
        .order_by(AnalysisSkillResult.id)
        .all()
    )
    assert len(rows) == 2
    assert rows[0].requirement == "Python"
    assert rows[0].matched_resume_skill == "Python"
    assert rows[0].similarity == 0.95
    assert rows[0].matched is True
    assert rows[1].requirement == "Bachelor's degree"
    assert rows[1].matched_resume_skill is None
    assert rows[1].matched is False


def test_save_analysis_result_persists_categories(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    rows = (
        db_session.query(AnalysisSkillResult)
        .filter_by(analysis_id=analysis.id)
        .order_by(AnalysisSkillResult.id)
        .all()
    )
    assert [r.category for r in rows] == ["skills", "education"]


# --------------------------------------------------------------------------
# 5 & 6: summary + recommendations JSON
# --------------------------------------------------------------------------


def test_save_analysis_result_persists_summary(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response(summary="A very specific summary sentence.")

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    summary_row = db_session.query(AnalysisSummary).filter_by(analysis_id=analysis.id).one()
    assert summary_row.summary_text == "A very specific summary sentence."


def test_save_analysis_result_persists_recommendations_json(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    summary_row = db_session.query(AnalysisSummary).filter_by(analysis_id=analysis.id).one()
    assert summary_row.recommendations_json == {
        "missing_required_skills": ["Go"],
        "missing_preferred_skills": ["Kubernetes"],
        "missing_certifications": ["PMP"],
        "missing_languages": ["German"],
    }


# --------------------------------------------------------------------------
# 7 & 8: load_analysis, without rerunning the matcher
# --------------------------------------------------------------------------


def test_load_analysis_reconstructs_result(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )

    loaded = analysis_repository.load_analysis(db_session, analysis.id)

    assert loaded is not None
    assert loaded.analysis_id == analysis.id
    assert loaded.resume_id == resume.id
    assert loaded.job_description_id == jd.id
    assert loaded.deterministic_score == match_result.deterministic_match.score
    assert loaded.semantic_score == match_result.semantic_match.semantic_score
    assert loaded.combined_score == match_result.combined_match_score
    assert loaded.summary == match_result.summary
    assert loaded.recommendations == {
        "missing_required_skills": ["Go"],
        "missing_preferred_skills": ["Kubernetes"],
        "missing_certifications": ["PMP"],
        "missing_languages": ["German"],
    }
    assert len(loaded.semantic_matches) == 2
    assert loaded.semantic_matches[0].requirement == "Python"
    assert loaded.semantic_matches[0].similarity == 0.95
    assert loaded.semantic_matches[0].matched is True
    assert loaded.semantic_matches[1].requirement == "Bachelor's degree"
    assert loaded.semantic_matches[1].matched is False


def test_load_analysis_returns_none_for_unknown_id(db_session):
    assert analysis_repository.load_analysis(db_session, uuid.uuid4()) is None


def test_load_analysis_does_not_rerun_matcher(db_session, monkeypatch):
    import app.services.resume_matcher as resume_matcher_module
    import app.services.semantic_matcher as semantic_matcher_module

    def boom(*args, **kwargs):
        raise AssertionError("load_analysis (or save_analysis_result) must never call the matcher")

    monkeypatch.setattr(resume_matcher_module, "match_resume_to_job", boom)
    monkeypatch.setattr(semantic_matcher_module, "compute_semantic_match", boom)

    resume, jd = _make_resume_and_jd(db_session)
    match_result = _make_match_response()

    analysis = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=match_result
    )
    loaded = analysis_repository.load_analysis(db_session, analysis.id)

    assert loaded is not None
    assert loaded.deterministic_score == 85.0


# --------------------------------------------------------------------------
# 9: multiple analyses for the same resume + JD are preserved
# --------------------------------------------------------------------------


def test_multiple_analyses_for_same_pair_are_preserved(db_session):
    resume, jd = _make_resume_and_jd(db_session)

    first = analysis_repository.save_analysis_result(
        db_session, resume_id=resume.id, job_description_id=jd.id, match_result=_make_match_response()
    )
    second = analysis_repository.save_analysis_result(
        db_session,
        resume_id=resume.id,
        job_description_id=jd.id,
        match_result=_make_match_response(combined_match_score=42.0),
    )

    assert first.id != second.id
    total = (
        db_session.query(ResumeAnalysis)
        .filter_by(resume_id=resume.id, job_description_id=jd.id)
        .count()
    )
    assert total == 2

    # Both must still be independently loadable with their own data intact.
    assert analysis_repository.load_analysis(db_session, first.id).combined_score == 81.25
    assert analysis_repository.load_analysis(db_session, second.id).combined_score == 42.0


# --------------------------------------------------------------------------
# 10: rollback on mid-transaction failure
# --------------------------------------------------------------------------


def test_transaction_rollback_leaves_no_partial_analysis_rows(db_session, monkeypatch):
    resume, jd = _make_resume_and_jd(db_session)

    original_add_all = db_session.add_all
    call_count = {"n": 0}

    def flaky_add_all(instances):
        call_count["n"] += 1
        # save_analysis_result's only add_all() call stages the
        # AnalysisSkillResult rows; fail there, i.e. after the
        # ResumeAnalysis row itself was already added and flushed, but
        # before either child table is touched - a genuine mid-sequence
        # failure point.
        if call_count["n"] == 1:
            raise RuntimeError("simulated failure while saving skill results")
        return original_add_all(instances)

    monkeypatch.setattr(db_session, "add_all", flaky_add_all)

    with pytest.raises(RuntimeError, match="simulated failure"):
        analysis_repository.save_analysis_result(
            db_session, resume_id=resume.id, job_description_id=jd.id, match_result=_make_match_response()
        )

    # No ResumeAnalysis, no skill results, no summary must survive.
    assert db_session.query(ResumeAnalysis).filter_by(resume_id=resume.id, job_description_id=jd.id).count() == 0
    assert db_session.query(AnalysisSkillResult).count() == 0
    assert db_session.query(AnalysisSummary).count() == 0


# --------------------------------------------------------------------------
# 11: list analyses, newest first
# --------------------------------------------------------------------------


def _make_analysis_at(db_session, resume, jd, when: datetime) -> ResumeAnalysis:
    # Explicit created_at (bypassing the server_default) because
    # PostgreSQL's now()/CURRENT_TIMESTAMP is frozen for the whole
    # transaction - multiple inserts in the same test transaction would
    # otherwise all get an identical timestamp, making "newest first"
    # unverifiable. Constructing rows directly (not via create_analysis)
    # is deliberate here, purely for deterministic ordering in this test.
    analysis = ResumeAnalysis(
        resume_id=resume.id,
        job_description_id=jd.id,
        deterministic_score=50.0,
        semantic_score=50.0,
        combined_score=50.0,
        created_at=when,
    )
    db_session.add(analysis)
    db_session.flush()
    return analysis


def test_list_analyses_for_resume_ordered_newest_first(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    oldest = _make_analysis_at(db_session, resume, jd, base)
    middle = _make_analysis_at(db_session, resume, jd, base + timedelta(hours=1))
    newest = _make_analysis_at(db_session, resume, jd, base + timedelta(hours=2))

    results = analysis_repository.list_analyses_for_resume(db_session, resume.id)

    assert [a.id for a in results] == [newest.id, middle.id, oldest.id]


def test_list_analyses_for_job_description_ordered_newest_first(db_session):
    resume, jd = _make_resume_and_jd(db_session)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    oldest = _make_analysis_at(db_session, resume, jd, base)
    newest = _make_analysis_at(db_session, resume, jd, base + timedelta(hours=1))

    results = analysis_repository.list_analyses_for_job_description(db_session, jd.id)

    assert [a.id for a in results] == [newest.id, oldest.id]


def test_list_analyses_for_resume_empty_when_none_exist(db_session):
    resume, _jd = _make_resume_and_jd(db_session)
    assert analysis_repository.list_analyses_for_resume(db_session, resume.id) == []
