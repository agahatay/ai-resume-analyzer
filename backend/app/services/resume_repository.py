"""Resume persistence layer (Phase 9C-1).

This is the only module that should issue SQLAlchemy writes for resumes.
Routers stay thin: they call these functions and translate the handful of
raised exceptions into HTTP responses. Nothing here touches the parsing
algorithm (app.services.resume_parser) or the matching/scoring formulas
(app.services.resume_matcher / semantic_matcher) - it only maps
``ParsedResume`` (the parser's existing output shape) onto the existing
Phase 9B ORM models, and back again.

Responsibilities:
- create_resume / get_resume / get_or_create_resume_for_parse
- save_parsed_resume_data (persist contact fields + all child collections)
- load_parsed_resume (reconstruct a ParsedResume from the database)

Transaction handling: every function that writes commits on success and
rolls back on any exception before re-raising it, so a caller never
observes (or leaves behind) a half-written resume.
"""

from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy.orm import Session, selectinload

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

# Placeholder filename used when parsed data is persisted without a prior
# POST /api/resume/upload call (i.e. no resume_id was supplied to
# POST /api/resume/parse), since Resume.original_filename is NOT NULL and
# there is no real uploaded file in that case.
UNLINKED_PARSE_FILENAME = "untitled-resume.txt"

_YEAR_RANGE_RE = re.compile(
    r"\b((?:19|20)\d{2})\b(?:\s*[-–—]\s*(?:\b((?:19|20)\d{2})\b|present|current))?",
    re.IGNORECASE,
)


class ResumeNotFoundError(Exception):
    """Raised when a resume_id is given but no such Resume row exists."""


# --------------------------------------------------------------------------
# Basic CRUD
# --------------------------------------------------------------------------


def create_resume(db: Session, *, original_filename: str, extracted_text: str) -> Resume:
    """Create and persist a new, otherwise-empty Resume row."""
    resume = Resume(original_filename=original_filename, extracted_text=extracted_text)
    db.add(resume)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(resume)
    return resume


def get_resume(db: Session, resume_id: uuid.UUID) -> Resume | None:
    """Fetch a Resume by id, or None if it does not exist."""
    return db.get(Resume, resume_id)


def get_or_create_resume_for_parse(db: Session, *, resume_id: uuid.UUID | None, text: str) -> Resume:
    """Resolve the Resume that a parse call should attach its data to.

    - resume_id given: fetch it (raising ResumeNotFoundError if missing),
      keeping its extracted_text in sync with the text actually parsed.
    - resume_id not given: create a fresh Resume from this text, since
      there was no prior upload to attach to.
    """
    if resume_id is not None:
        resume = get_resume(db, resume_id)
        if resume is None:
            raise ResumeNotFoundError(f"No resume found with id {resume_id}.")
        if resume.extracted_text != text:
            resume.extracted_text = text
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
            db.refresh(resume)
        return resume

    return create_resume(db, original_filename=UNLINKED_PARSE_FILENAME, extracted_text=text)


# --------------------------------------------------------------------------
# Saving parsed data
# --------------------------------------------------------------------------


def _replace_children(db: Session, model_cls: type, resume_id: uuid.UUID, new_rows: list) -> None:
    """Delete all of a resume's existing rows for one child table, then
    stage the freshly-parsed replacements.

    Deleting first and flushing immediately (rather than relying on
    relationship-collection replacement + delete-orphan cascade) avoids a
    transient unique-constraint conflict when an old and new row for the
    same resume happen to have the same natural key (e.g. an unchanged
    skill re-parsed from the same text) - and it means re-parsing the same
    resume never duplicates child rows, since the old set is always fully
    cleared before the new set is added.
    """
    db.query(model_cls).filter(model_cls.resume_id == resume_id).delete(synchronize_session=False)
    db.flush()
    if new_rows:
        db.add_all(new_rows)


def _parse_year_range(dates_text: str | None) -> tuple[date | None, date | None]:
    """Best-effort extraction of (start_date, end_date) from the parser's
    free-text date range (e.g. "2019 - 2021", "2020", "2020 - Present").

    The parser (app.services.resume_parser) only ever extracts bare years,
    never months/days, so representing each as Jan 1st loses no precision
    the parser had in the first place. "Present"/"current" and a
    genuinely-unparseable range both collapse to a NULL end_date - see the
    module-level docstring / Phase 9C-1 report for this known limitation.
    """
    if not dates_text:
        return None, None
    match = _YEAR_RANGE_RE.search(dates_text)
    if not match:
        return None, None
    start = date(int(match.group(1)), 1, 1)
    end = date(int(match.group(2)), 1, 1) if match.group(2) else None
    return start, end


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def save_parsed_resume_data(db: Session, resume: Resume, parsed: ParsedResume) -> Resume:
    """Persist a ParsedResume's contact fields and all child collections
    onto an existing Resume row.

    Re-running this for the same resume replaces (not appends to) every
    child collection, so parsing the same resume twice never duplicates
    skills/education/experience/projects/certifications/languages.
    Everything happens in one transaction: on any failure the session is
    rolled back and the resume is left exactly as it was before this call.
    """
    try:
        resume.full_name = parsed.full_name
        resume.email = parsed.email
        resume.phone = parsed.phone
        resume.location = parsed.location

        _replace_children(
            db,
            ResumeSkill,
            resume.id,
            [ResumeSkill(resume_id=resume.id, skill=skill) for skill in _dedupe_preserve_order(parsed.skills)],
        )

        education_rows = []
        for entry in parsed.education:
            start_date, end_date = _parse_year_range(entry.dates)
            education_rows.append(
                ResumeEducation(
                    resume_id=resume.id,
                    degree=entry.degree,
                    institution=entry.institution,
                    start_date=start_date,
                    end_date=end_date,
                    # The parser's raw_text has no dedicated column in the
                    # Phase 9B schema; description is otherwise unused by
                    # EducationEntry, so it's the best-fit place to keep it
                    # verbatim (see load_parsed_resume for the reverse map).
                    description=entry.raw_text,
                )
            )
        _replace_children(db, ResumeEducation, resume.id, education_rows)

        experience_rows = []
        for entry in parsed.work_experience:
            start_date, end_date = _parse_year_range(entry.dates)
            experience_rows.append(
                ResumeExperience(
                    resume_id=resume.id,
                    job_title=entry.title,
                    company=entry.organization,
                    start_date=start_date,
                    end_date=end_date,
                    description=entry.raw_text,
                )
            )
        _replace_children(db, ResumeExperience, resume.id, experience_rows)

        _replace_children(
            db,
            ResumeProject,
            resume.id,
            [
                ResumeProject(resume_id=resume.id, name=entry.name, description=entry.description)
                for entry in parsed.projects
            ],
        )

        _replace_children(
            db,
            ResumeCertification,
            resume.id,
            [
                ResumeCertification(resume_id=resume.id, name=name)
                for name in _dedupe_preserve_order(parsed.certifications)
            ],
        )

        _replace_children(
            db,
            ResumeLanguage,
            resume.id,
            [
                ResumeLanguage(resume_id=resume.id, language=language)
                for language in _dedupe_preserve_order(parsed.languages)
            ],
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(resume)
    return resume


# --------------------------------------------------------------------------
# Reconstruction
# --------------------------------------------------------------------------


def _format_year_range(start: date | None, end: date | None) -> str | None:
    """Inverse of _parse_year_range, to the extent that's possible: we
    cannot tell "Present" apart from "no end year was parsed" once both
    have collapsed to a NULL end_date (documented limitation)."""
    if start and end:
        return f"{start.year} - {end.year}"
    if start:
        return str(start.year)
    return None


def _fallback_raw_text(*parts: str | None) -> str:
    """EducationEntry/ExperienceEntry/ProjectEntry.raw_text is a required
    field, but a row's description could in principle be NULL (e.g. a row
    created outside save_parsed_resume_data). Synthesize something
    non-empty from whatever fields are available rather than fail."""
    joined = " - ".join(part for part in parts if part)
    return joined or "(no raw text available)"


def load_parsed_resume(db: Session, resume_id: uuid.UUID) -> ParsedResume | None:
    """Reconstruct a ParsedResume from what's stored in PostgreSQL for a
    given resume, or None if no such resume exists.

    Known lossy spots versus the original parser output, both inherent to
    the Phase 9B schema (not something this function can recover):
    - EducationEntry/ExperienceEntry.raw_text is restored verbatim from
      `description` (which save_parsed_resume_data always populates for
      rows it wrote), but `dates` is re-derived from start_date/end_date
      and so loses "Present/current" phrasing.
    - ProjectEntry.raw_text has no backing column at all (name and
      description already map to the parser's own project fields), so
      it is synthesized from name/description rather than restored.
    """
    resume = db.get(
        Resume,
        resume_id,
        options=[
            selectinload(Resume.skills),
            selectinload(Resume.education),
            selectinload(Resume.work_experience),
            selectinload(Resume.projects),
            selectinload(Resume.certifications),
            selectinload(Resume.languages),
        ],
    )
    if resume is None:
        return None

    return ParsedResume(
        full_name=resume.full_name,
        email=resume.email,
        phone=resume.phone,
        location=resume.location,
        skills=[row.skill for row in resume.skills],
        education=[
            EducationEntry(
                institution=row.institution,
                degree=row.degree,
                dates=_format_year_range(row.start_date, row.end_date),
                raw_text=row.description
                if row.description is not None
                else _fallback_raw_text(row.degree, row.institution),
            )
            for row in resume.education
        ],
        work_experience=[
            ExperienceEntry(
                title=row.job_title,
                organization=row.company,
                dates=_format_year_range(row.start_date, row.end_date),
                raw_text=row.description
                if row.description is not None
                else _fallback_raw_text(row.job_title, row.company),
            )
            for row in resume.work_experience
        ],
        projects=[
            ProjectEntry(
                name=row.name,
                description=row.description,
                raw_text=row.description if row.description is not None else _fallback_raw_text(row.name),
            )
            for row in resume.projects
        ],
        certifications=[row.name for row in resume.certifications],
        languages=[row.language for row in resume.languages],
        resume_id=resume.id,
    )
