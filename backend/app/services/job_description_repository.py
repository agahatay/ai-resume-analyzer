"""Job description persistence layer (Phase 9C-2).

Mirrors the design of resume_repository.py (Phase 9C-1): this is the only
module that should issue SQLAlchemy writes for job descriptions. Routers
stay thin and translate the one raised exception into an HTTP response.
Nothing here touches the parsing algorithm
(app.services.job_description_parser) or the matching/scoring formulas.

Responsibilities:
- create_job_description / get_job_description /
  get_or_create_job_description_for_parse
- save_parsed_job_description (persist job_title + all requirements)
- load_parsed_job_description (reconstruct a ParsedJobDescription)

Unlike resume child tables, JobRequirement has no per-category free-text
fields that don't map onto ParsedJobDescription (no resume-style "raw_text"
gap) - every requirement is just (requirement, category), and the six
category values already correspond 1:1 with ParsedJobDescription's six
list fields. So reconstruction here is exact, not best-effort.

Transaction handling: every function that writes commits on success and
rolls back on any exception before re-raising it, so a caller never
observes (or leaves behind) a half-written job description.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.job_description import JobDescription, JobRequirement
from app.schemas.job_description import ParsedJobDescription

# Maps each ParsedJobDescription list field to the JobRequirement.category
# value it round-trips through. Order here also fixes the order in which
# categories are (re)written on every save, though within-category order
# is preserved via each list's own order and the id-ordered relationship.
_CATEGORY_TO_FIELD = {
    "required_skill": "required_skills",
    "preferred_skill": "preferred_skills",
    "education": "education_requirements",
    "experience": "experience_requirements",
    "certification": "certifications",
    "language": "languages",
}


class JobDescriptionNotFoundError(Exception):
    """Raised when a job_description_id is given but no such row exists."""


# --------------------------------------------------------------------------
# Basic CRUD
# --------------------------------------------------------------------------


def create_job_description(
    db: Session, *, raw_text: str, job_title: str | None = None, user_id: uuid.UUID | None = None
) -> JobDescription:
    """Create and persist a new JobDescription row.

    user_id defaults to None only for callers without an authenticated
    user in scope (some direct repository-level tests, and the
    job_description_id-less case of get_or_create_job_description_for_parse
    - though as of Phase 10B every real HTTP caller passes a real user_id,
    since POST /api/job-description/parse now requires authentication).
    """
    job_description = JobDescription(raw_text=raw_text, job_title=job_title, user_id=user_id)
    db.add(job_description)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(job_description)
    return job_description


def get_job_description(db: Session, job_description_id: uuid.UUID) -> JobDescription | None:
    """Fetch a JobDescription by id, or None if it does not exist.
    Ownership-blind on purpose - see get_resume's docstring for why."""
    return db.get(JobDescription, job_description_id)


def get_or_create_job_description_for_parse(
    db: Session, *, job_description_id: uuid.UUID | None, text: str, user_id: uuid.UUID
) -> JobDescription:
    """Resolve the JobDescription that a parse call should attach its
    data to, enforcing ownership throughout.

    - job_description_id given: fetch it and verify
      job_description.user_id == user_id, keeping its raw_text in sync
      with the text actually parsed. A job description that doesn't
      exist and one that exists but belongs to someone else raise the
      exact same JobDescriptionNotFoundError with the same message - the
      same deliberate, consistent policy resume_repository uses (see
      Phase 10B report).
    - job_description_id not given: create a fresh JobDescription owned
      by user_id.

    user_id is never taken from anywhere but the caller's own verified
    identity (the router passes current_user.id from get_current_user) -
    never from request body data.
    """
    if job_description_id is not None:
        job_description = get_job_description(db, job_description_id)
        if job_description is None or job_description.user_id != user_id:
            raise JobDescriptionNotFoundError(f"No job description found with id {job_description_id}.")
        if job_description.raw_text != text:
            job_description.raw_text = text
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
            db.refresh(job_description)
        return job_description

    return create_job_description(db, raw_text=text, user_id=user_id)


# --------------------------------------------------------------------------
# Saving parsed data
# --------------------------------------------------------------------------


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _replace_requirements(db: Session, job_description_id: uuid.UUID, new_rows: list[JobRequirement]) -> None:
    """Delete all of a job description's existing requirement rows, then
    stage the freshly-parsed replacements.

    Deleting first and flushing immediately (rather than relying on
    relationship-collection replacement + delete-orphan cascade) means
    re-parsing the same job description never duplicates requirements,
    since the old set is always fully cleared before the new set is added.
    """
    db.query(JobRequirement).filter(JobRequirement.job_description_id == job_description_id).delete(
        synchronize_session=False
    )
    db.flush()
    if new_rows:
        db.add_all(new_rows)


def save_parsed_job_description(
    db: Session, job_description: JobDescription, parsed: ParsedJobDescription
) -> JobDescription:
    """Persist a ParsedJobDescription's job_title and every requirement
    onto an existing JobDescription row.

    Re-running this for the same job description replaces (not appends
    to) its requirements: all existing JobRequirement rows are deleted
    and the newly parsed set is inserted, so parsing the same job
    description twice never duplicates requirements. Everything happens
    in one transaction: on any failure the session is rolled back and the
    job description is left exactly as it was before this call.
    """
    try:
        job_description.job_title = parsed.job_title

        new_rows = [
            JobRequirement(job_description_id=job_description.id, requirement=item, category=category)
            for category, field_name in _CATEGORY_TO_FIELD.items()
            for item in _dedupe_preserve_order(getattr(parsed, field_name))
        ]

        _replace_requirements(db, job_description.id, new_rows)

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(job_description)
    return job_description


# --------------------------------------------------------------------------
# Reconstruction
# --------------------------------------------------------------------------


def load_parsed_job_description(db: Session, job_description_id: uuid.UUID) -> ParsedJobDescription | None:
    """Reconstruct a ParsedJobDescription from what's stored in
    PostgreSQL for a given job description, or None if it doesn't exist.

    This reconstruction is exact (not best-effort): every JobRequirement's
    (requirement, category) pair maps directly back onto one of
    ParsedJobDescription's six list fields, with no information loss.
    """
    job_description = db.get(
        JobDescription,
        job_description_id,
        options=[selectinload(JobDescription.requirements)],
    )
    if job_description is None:
        return None

    buckets: dict[str, list[str]] = {category: [] for category in _CATEGORY_TO_FIELD}
    for row in job_description.requirements:
        # Defensive: the CHECK constraint guarantees category is one of
        # our six values, but guard anyway rather than KeyError on a row
        # written by some other, future code path.
        buckets.setdefault(row.category, []).append(row.requirement)

    return ParsedJobDescription(
        job_title=job_description.job_title,
        required_skills=buckets["required_skill"],
        preferred_skills=buckets["preferred_skill"],
        education_requirements=buckets["education"],
        experience_requirements=buckets["experience"],
        certifications=buckets["certification"],
        languages=buckets["language"],
        job_description_id=job_description.id,
    )
