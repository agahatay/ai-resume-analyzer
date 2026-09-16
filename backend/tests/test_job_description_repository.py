"""Phase 9C-2: integration tests for app.services.job_description_repository.

Mirrors tests/test_resume_repository.py's approach: these exercise the
repository directly against the real PostgreSQL database inside the
db_session fixture's SAVEPOINT-based transaction, which is always rolled
back at teardown, so nothing here is ever actually persisted.
"""

import uuid

import pytest

from app.models.job_description import JobDescription, JobRequirement
from app.schemas.job_description import ParsedJobDescription
from app.services import job_description_repository


def _make_parsed_jd(**overrides) -> ParsedJobDescription:
    defaults = dict(
        job_title="Senior Backend Engineer",
        required_skills=["Python", "PostgreSQL", "FastAPI"],
        preferred_skills=["Docker", "Kubernetes"],
        education_requirements=["Bachelor's degree in Computer Science"],
        experience_requirements=["5+ years of experience"],
        certifications=["AWS Certified Solutions Architect"],
        languages=["English"],
    )
    defaults.update(overrides)
    return ParsedJobDescription(**defaults)


# --------------------------------------------------------------------------
# create / get
# --------------------------------------------------------------------------


def test_create_job_description_persists_row(db_session):
    jd = job_description_repository.create_job_description(
        db_session, raw_text="We need a Python developer.", job_title="Python Developer"
    )
    assert jd.id is not None
    assert jd.created_at is not None
    assert jd.updated_at is not None

    fetched = db_session.get(JobDescription, jd.id)
    assert fetched is not None
    assert fetched.raw_text == "We need a Python developer."
    assert fetched.job_title == "Python Developer"


def test_get_job_description_returns_none_for_unknown_id(db_session):
    assert job_description_repository.get_job_description(db_session, uuid.uuid4()) is None


# --------------------------------------------------------------------------
# get_or_create_job_description_for_parse
# --------------------------------------------------------------------------


def test_get_or_create_creates_new_jd_when_no_id_given(db_session):
    jd = job_description_repository.get_or_create_job_description_for_parse(
        db_session, job_description_id=None, text="some jd text"
    )
    assert jd.id is not None
    assert jd.raw_text == "some jd text"
    assert jd.job_title is None


def test_get_or_create_raises_for_unknown_job_description_id(db_session):
    with pytest.raises(job_description_repository.JobDescriptionNotFoundError):
        job_description_repository.get_or_create_job_description_for_parse(
            db_session, job_description_id=uuid.uuid4(), text="x"
        )


def test_get_or_create_returns_existing_and_syncs_text(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="old text")
    fetched = job_description_repository.get_or_create_job_description_for_parse(
        db_session, job_description_id=jd.id, text="new text"
    )
    assert fetched.id == jd.id
    assert fetched.raw_text == "new text"


# --------------------------------------------------------------------------
# save_parsed_job_description: persistence of every field group
# --------------------------------------------------------------------------


def test_save_parsed_job_description_persists_job_title(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    fetched = db_session.get(JobDescription, jd.id)
    assert fetched.job_title == "Senior Backend Engineer"


def test_save_parsed_job_description_persists_required_skills(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = (
        db_session.query(JobRequirement)
        .filter_by(job_description_id=jd.id, category="required_skill")
        .order_by(JobRequirement.id)
        .all()
    )
    assert [r.requirement for r in rows] == ["Python", "PostgreSQL", "FastAPI"]


def test_save_parsed_job_description_persists_preferred_skills(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = (
        db_session.query(JobRequirement)
        .filter_by(job_description_id=jd.id, category="preferred_skill")
        .order_by(JobRequirement.id)
        .all()
    )
    assert [r.requirement for r in rows] == ["Docker", "Kubernetes"]


def test_save_parsed_job_description_persists_education_requirements(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="education").all()
    assert [r.requirement for r in rows] == ["Bachelor's degree in Computer Science"]


def test_save_parsed_job_description_persists_experience_requirements(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="experience").all()
    assert [r.requirement for r in rows] == ["5+ years of experience"]


def test_save_parsed_job_description_persists_certifications(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="certification").all()
    assert [r.requirement for r in rows] == ["AWS Certified Solutions Architect"]


def test_save_parsed_job_description_persists_languages(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    rows = db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="language").all()
    assert [r.requirement for r in rows] == ["English"]


# --------------------------------------------------------------------------
# Reconstruction
# --------------------------------------------------------------------------


def test_load_parsed_job_description_reconstructs_exactly(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    original = _make_parsed_jd()
    job_description_repository.save_parsed_job_description(db_session, jd, original)

    reconstructed = job_description_repository.load_parsed_job_description(db_session, jd.id)

    assert reconstructed is not None
    assert reconstructed.job_description_id == jd.id
    assert reconstructed.job_title == original.job_title
    assert reconstructed.required_skills == original.required_skills
    assert reconstructed.preferred_skills == original.preferred_skills
    assert reconstructed.education_requirements == original.education_requirements
    assert reconstructed.experience_requirements == original.experience_requirements
    assert reconstructed.certifications == original.certifications
    assert reconstructed.languages == original.languages


def test_load_parsed_job_description_returns_none_for_unknown_id(db_session):
    assert job_description_repository.load_parsed_job_description(db_session, uuid.uuid4()) is None


# --------------------------------------------------------------------------
# Re-parsing: no duplicates, full replacement
# --------------------------------------------------------------------------


def test_reparsing_same_jd_does_not_duplicate_requirements(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    parsed = _make_parsed_jd()

    job_description_repository.save_parsed_job_description(db_session, jd, parsed)
    job_description_repository.save_parsed_job_description(db_session, jd, parsed)  # re-parse identical data

    total = db_session.query(JobRequirement).filter_by(job_description_id=jd.id).count()
    assert total == 9  # 3 + 2 + 1 + 1 + 1 + 1, not doubled


def test_reparsing_replaces_requirements_with_new_data(db_session):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    updated = _make_parsed_jd(required_skills=["Go"], certifications=[], languages=["German", "French"])
    job_description_repository.save_parsed_job_description(db_session, jd, updated)

    required = db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="required_skill").all()
    assert [r.requirement for r in required] == ["Go"]
    assert db_session.query(JobRequirement).filter_by(job_description_id=jd.id, category="certification").count() == 0
    languages = (
        db_session.query(JobRequirement)
        .filter_by(job_description_id=jd.id, category="language")
        .order_by(JobRequirement.id)
        .all()
    )
    assert [r.requirement for r in languages] == ["German", "French"]


# --------------------------------------------------------------------------
# Transaction handling
# --------------------------------------------------------------------------


def test_transaction_rollback_leaves_no_partial_requirements_on_failure(db_session, monkeypatch):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure while replacing requirements")

    monkeypatch.setattr(job_description_repository, "_replace_requirements", boom)

    with pytest.raises(RuntimeError, match="simulated failure"):
        job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    fetched = db_session.get(JobDescription, jd.id)
    assert fetched.job_title is None
    assert db_session.query(JobRequirement).filter_by(job_description_id=jd.id).count() == 0


def test_transaction_rollback_preserves_previous_data_on_reparse_failure(db_session, monkeypatch):
    jd = job_description_repository.create_job_description(db_session, raw_text="text")
    job_description_repository.save_parsed_job_description(db_session, jd, _make_parsed_jd())

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure on reparse")

    monkeypatch.setattr(job_description_repository, "_replace_requirements", boom)

    updated = _make_parsed_jd(required_skills=["Go"], job_title="Someone Else's Title")
    with pytest.raises(RuntimeError, match="simulated failure"):
        job_description_repository.save_parsed_job_description(db_session, jd, updated)

    fetched = db_session.get(JobDescription, jd.id)
    assert fetched.job_title == "Senior Backend Engineer"
    required = (
        db_session.query(JobRequirement)
        .filter_by(job_description_id=jd.id, category="required_skill")
        .order_by(JobRequirement.id)
        .all()
    )
    assert [r.requirement for r in required] == ["Python", "PostgreSQL", "FastAPI"]
