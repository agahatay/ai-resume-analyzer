"""Phase 9C-1: integration tests for app.services.resume_repository.

These exercise the repository directly against the real PostgreSQL
database (there's no meaningful in-memory substitute for testing real
commit/rollback and cascade behavior). Every test runs inside the
db_session fixture's SAVEPOINT-based transaction, which is always rolled
back at teardown, so nothing here is ever actually persisted - including
the internal db.commit() calls save_parsed_resume_data/create_resume make,
which SQLAlchemy's join_transaction_mode="create_savepoint" turns into a
release-and-reopen of that same savepoint rather than a real COMMIT.
"""

import uuid

import pytest

from app.models.resume import (
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeLanguage,
    ResumeProject,
    ResumeSkill,
)
from app.schemas.resume import EducationEntry, ExperienceEntry, ParsedResume, ProjectEntry
from app.services import resume_repository


def _make_parsed_resume(**overrides) -> ParsedResume:
    defaults = dict(
        full_name="Jane Doe",
        email="jane.doe@example.com",
        phone="+1 512 555 0100",
        location="Austin, TX",
        skills=["Python", "SQL", "FastAPI"],
        education=[
            EducationEntry(
                institution="MIT",
                degree="BSc Computer Science",
                dates="2018 - 2022",
                raw_text="BSc Computer Science - MIT\n2018 - 2022",
            )
        ],
        work_experience=[
            ExperienceEntry(
                title="Software Engineer",
                organization="Acme Corp",
                dates="2022 - Present",
                raw_text="Software Engineer - Acme Corp\n2022 - Present\nBuilt things.",
            )
        ],
        projects=[
            ProjectEntry(
                name="Resume Analyzer",
                description="An AI-powered resume analyzer.",
                raw_text="Resume Analyzer: An AI-powered resume analyzer.",
            )
        ],
        certifications=["AWS Certified Developer"],
        languages=["English"],
    )
    defaults.update(overrides)
    return ParsedResume(**defaults)


# --------------------------------------------------------------------------
# create / get
# --------------------------------------------------------------------------


def test_create_resume_persists_row(db_session):
    resume = resume_repository.create_resume(
        db_session, original_filename="resume.pdf", extracted_text="Jane Doe, Python developer."
    )
    assert resume.id is not None
    assert resume.created_at is not None
    assert resume.updated_at is not None

    fetched = db_session.get(Resume, resume.id)
    assert fetched is not None
    assert fetched.original_filename == "resume.pdf"
    assert fetched.extracted_text == "Jane Doe, Python developer."


def test_get_resume_returns_none_for_unknown_id(db_session):
    assert resume_repository.get_resume(db_session, uuid.uuid4()) is None


# --------------------------------------------------------------------------
# get_or_create_resume_for_parse
# --------------------------------------------------------------------------


def test_get_or_create_creates_new_resume_when_no_id_given(db_session):
    resume = resume_repository.get_or_create_resume_for_parse(db_session, resume_id=None, text="some text")
    assert resume.id is not None
    assert resume.extracted_text == "some text"
    assert resume.original_filename == resume_repository.UNLINKED_PARSE_FILENAME


def test_get_or_create_raises_for_unknown_resume_id(db_session):
    with pytest.raises(resume_repository.ResumeNotFoundError):
        resume_repository.get_or_create_resume_for_parse(db_session, resume_id=uuid.uuid4(), text="x")


def test_get_or_create_returns_existing_and_syncs_text(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="old text")
    fetched = resume_repository.get_or_create_resume_for_parse(db_session, resume_id=resume.id, text="new text")
    assert fetched.id == resume.id
    assert fetched.extracted_text == "new text"


# --------------------------------------------------------------------------
# save_parsed_resume_data: persistence of every field group
# --------------------------------------------------------------------------


def test_save_parsed_resume_data_persists_contact_fields(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    fetched = db_session.get(Resume, resume.id)
    assert fetched.full_name == "Jane Doe"
    assert fetched.email == "jane.doe@example.com"
    assert fetched.phone == "+1 512 555 0100"
    assert fetched.location == "Austin, TX"


def test_save_parsed_resume_data_persists_skills(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    skills = db_session.query(ResumeSkill).filter_by(resume_id=resume.id).order_by(ResumeSkill.id).all()
    assert [s.skill for s in skills] == ["Python", "SQL", "FastAPI"]
    assert all(s.source == "parsed" for s in skills)


def test_save_parsed_resume_data_persists_education(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    rows = db_session.query(ResumeEducation).filter_by(resume_id=resume.id).all()
    assert len(rows) == 1
    assert rows[0].institution == "MIT"
    assert rows[0].degree == "BSc Computer Science"
    assert rows[0].start_date.year == 2018
    assert rows[0].end_date.year == 2022
    assert "MIT" in rows[0].description


def test_save_parsed_resume_data_persists_experience(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    rows = db_session.query(ResumeExperience).filter_by(resume_id=resume.id).all()
    assert len(rows) == 1
    assert rows[0].job_title == "Software Engineer"
    assert rows[0].company == "Acme Corp"
    assert rows[0].start_date.year == 2022
    assert rows[0].end_date is None  # "Present" collapses to no end date (documented limitation)
    assert "Built things." in rows[0].description


def test_save_parsed_resume_data_persists_projects(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    rows = db_session.query(ResumeProject).filter_by(resume_id=resume.id).all()
    assert len(rows) == 1
    assert rows[0].name == "Resume Analyzer"
    assert rows[0].description == "An AI-powered resume analyzer."


def test_save_parsed_resume_data_persists_certifications(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    rows = db_session.query(ResumeCertification).filter_by(resume_id=resume.id).all()
    assert [r.name for r in rows] == ["AWS Certified Developer"]


def test_save_parsed_resume_data_persists_languages(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    rows = db_session.query(ResumeLanguage).filter_by(resume_id=resume.id).all()
    assert [r.language for r in rows] == ["English"]


# --------------------------------------------------------------------------
# Reconstruction
# --------------------------------------------------------------------------


def test_load_parsed_resume_reconstructs_parsed_resume(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    original = _make_parsed_resume()
    resume_repository.save_parsed_resume_data(db_session, resume, original)

    reconstructed = resume_repository.load_parsed_resume(db_session, resume.id)

    assert reconstructed is not None
    assert reconstructed.resume_id == resume.id
    assert reconstructed.full_name == original.full_name
    assert reconstructed.email == original.email
    assert reconstructed.phone == original.phone
    assert reconstructed.location == original.location
    assert reconstructed.skills == original.skills
    assert reconstructed.certifications == original.certifications
    assert reconstructed.languages == original.languages

    assert len(reconstructed.education) == 1
    assert reconstructed.education[0].institution == original.education[0].institution
    assert reconstructed.education[0].degree == original.education[0].degree
    assert reconstructed.education[0].raw_text == original.education[0].raw_text  # stored verbatim

    assert len(reconstructed.work_experience) == 1
    assert reconstructed.work_experience[0].title == original.work_experience[0].title
    assert reconstructed.work_experience[0].organization == original.work_experience[0].organization
    assert reconstructed.work_experience[0].raw_text == original.work_experience[0].raw_text

    assert len(reconstructed.projects) == 1
    assert reconstructed.projects[0].name == original.projects[0].name
    assert reconstructed.projects[0].description == original.projects[0].description


def test_load_parsed_resume_returns_none_for_unknown_id(db_session):
    assert resume_repository.load_parsed_resume(db_session, uuid.uuid4()) is None


# --------------------------------------------------------------------------
# Re-parsing: no duplicates, full replacement
# --------------------------------------------------------------------------


def test_reparsing_same_resume_does_not_duplicate_child_rows(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    parsed = _make_parsed_resume()

    resume_repository.save_parsed_resume_data(db_session, resume, parsed)
    resume_repository.save_parsed_resume_data(db_session, resume, parsed)  # re-parse identical data

    assert db_session.query(ResumeSkill).filter_by(resume_id=resume.id).count() == 3
    assert db_session.query(ResumeEducation).filter_by(resume_id=resume.id).count() == 1
    assert db_session.query(ResumeExperience).filter_by(resume_id=resume.id).count() == 1
    assert db_session.query(ResumeProject).filter_by(resume_id=resume.id).count() == 1
    assert db_session.query(ResumeCertification).filter_by(resume_id=resume.id).count() == 1
    assert db_session.query(ResumeLanguage).filter_by(resume_id=resume.id).count() == 1


def test_reparsing_replaces_child_rows_with_new_data(db_session):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    updated = _make_parsed_resume(skills=["Rust"], certifications=[], languages=["German", "French"])
    resume_repository.save_parsed_resume_data(db_session, resume, updated)

    skills = db_session.query(ResumeSkill).filter_by(resume_id=resume.id).all()
    assert [s.skill for s in skills] == ["Rust"]
    assert db_session.query(ResumeCertification).filter_by(resume_id=resume.id).count() == 0
    languages = db_session.query(ResumeLanguage).filter_by(resume_id=resume.id).order_by(ResumeLanguage.id).all()
    assert [lang.language for lang in languages] == ["German", "French"]


# --------------------------------------------------------------------------
# Transaction handling
# --------------------------------------------------------------------------


def test_transaction_rollback_leaves_no_partial_children_on_failure(db_session, monkeypatch):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")

    original_replace_children = resume_repository._replace_children

    def flaky_replace_children(db, model_cls, resume_id, new_rows):
        if model_cls is ResumeProject:
            raise RuntimeError("simulated failure while saving projects")
        return original_replace_children(db, model_cls, resume_id, new_rows)

    monkeypatch.setattr(resume_repository, "_replace_children", flaky_replace_children)

    with pytest.raises(RuntimeError, match="simulated failure"):
        resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    # Nothing from the failed call should have stuck - not the contact
    # fields, not the skills/education/experience staged before the
    # failure point, and obviously not the projects that triggered it.
    fetched = db_session.get(Resume, resume.id)
    assert fetched.full_name is None
    assert fetched.email is None
    assert db_session.query(ResumeSkill).filter_by(resume_id=resume.id).count() == 0
    assert db_session.query(ResumeEducation).filter_by(resume_id=resume.id).count() == 0
    assert db_session.query(ResumeExperience).filter_by(resume_id=resume.id).count() == 0
    assert db_session.query(ResumeProject).filter_by(resume_id=resume.id).count() == 0


def test_transaction_rollback_preserves_previous_data_on_reparse_failure(db_session, monkeypatch):
    resume = resume_repository.create_resume(db_session, original_filename="a.pdf", extracted_text="text")
    resume_repository.save_parsed_resume_data(db_session, resume, _make_parsed_resume())

    original_replace_children = resume_repository._replace_children

    def flaky_replace_children(db, model_cls, resume_id, new_rows):
        if model_cls is ResumeCertification:
            raise RuntimeError("simulated failure while saving certifications")
        return original_replace_children(db, model_cls, resume_id, new_rows)

    monkeypatch.setattr(resume_repository, "_replace_children", flaky_replace_children)

    updated = _make_parsed_resume(skills=["Go"], full_name="Someone Else")
    with pytest.raises(RuntimeError, match="simulated failure"):
        resume_repository.save_parsed_resume_data(db_session, resume, updated)

    # The failed re-parse must not have touched the resume at all: the
    # original successful parse's data is still exactly as it was.
    fetched = db_session.get(Resume, resume.id)
    assert fetched.full_name == "Jane Doe"
    skills = db_session.query(ResumeSkill).filter_by(resume_id=resume.id).order_by(ResumeSkill.id).all()
    assert [s.skill for s in skills] == ["Python", "SQL", "FastAPI"]
