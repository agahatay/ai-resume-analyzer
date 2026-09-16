"""Phase 9D: full end-to-end workflow test.

Runs the complete real pipeline exactly as the frontend now does it -
upload a real PDF, parse the resume, parse a realistic job description,
match them - using only the ids each step's own response returns (never
inventing one), then verifies the database contains exactly one resume,
one job description, and one analysis. A second match against the same
pair must add a second analysis without duplicating the resume or job
description.

No mocking of the matcher: this is the same real deterministic + semantic
pipeline exercised in tests/test_analysis_api_persistence.py.
"""

from app.core.database import SessionLocal
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.analysis import ResumeAnalysis
from tests.conftest import make_test_pdf_bytes

RESUME_TEXT = (
    "Alex Rivera\n"
    "alex.rivera@example.com\n"
    "Seattle, WA\n"
    "\n"
    "SKILLS\n"
    "Python, SQL, FastAPI, Docker\n"
    "\n"
    "EDUCATION\n"
    "BSc Computer Science - University of Washington\n"
    "2016 - 2020\n"
    "\n"
    "EXPERIENCE\n"
    "Backend Engineer - Acme Corp\n"
    "2020 - Present\n"
    "Built and maintained REST APIs serving millions of requests per day.\n"
)

JD_TEXT = (
    "We are hiring a Backend Engineer.\n"
    "\n"
    "Required Skills:\n"
    "Python, SQL, FastAPI\n"
    "\n"
    "Preferred Skills:\n"
    "Docker\n"
    "\n"
    "Education:\n"
    "Bachelor's degree in Computer Science\n"
    "\n"
    "Experience:\n"
    "2+ years of experience\n"
)


def _count_rows(session):
    return {
        "resumes": session.query(Resume).count(),
        "job_descriptions": session.query(JobDescription).count(),
        "analyses": session.query(ResumeAnalysis).count(),
    }


def test_full_upload_parse_match_workflow_persists_exactly_one_of_each(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()

    # 1. Upload the real PDF.
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    upload_body = upload_resp.json()
    resume_id = upload_body["resume_id"]
    cleanup_resumes.append(resume_id)

    # 2. Parse the resume, linked to that exact upload via resume_id.
    parse_resume_resp = client.post(
        "/api/resume/parse",
        json={"text": upload_body["extracted_text"], "resume_id": resume_id},
        headers=headers,
    )
    assert parse_resume_resp.status_code == 200
    parsed_resume = parse_resume_resp.json()
    assert parsed_resume["resume_id"] == resume_id

    # 3. Parse the job description.
    parse_jd_resp = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert parse_jd_resp.status_code == 200
    parsed_jd = parse_jd_resp.json()
    jd_id = parsed_jd["job_description_id"]
    cleanup_job_descriptions.append(jd_id)

    # 4. Match, using exactly the ids the previous two steps returned.
    match_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers,
    )
    assert match_resp.status_code == 200
    match_body = match_resp.json()
    analysis_id = match_body["analysis_id"]
    assert analysis_id is not None

    # Database must now contain exactly one resume, one job description,
    # and one analysis - nothing duplicated, nothing invented.
    session = SessionLocal()
    try:
        counts = _count_rows(session)
        assert counts == {"resumes": 1, "job_descriptions": 1, "analyses": 1}

        resume_row = session.get(Resume, resume_id)
        assert resume_row is not None
        assert resume_row.email == "alex.rivera@example.com"

        jd_row = session.get(JobDescription, jd_id)
        assert jd_row is not None
        assert jd_row.job_title is not None

        analysis_row = session.get(ResumeAnalysis, analysis_id)
        assert analysis_row is not None
        assert str(analysis_row.resume_id) == resume_id
        assert str(analysis_row.job_description_id) == jd_id
    finally:
        session.close()

    # 5. Match again, without re-uploading or re-parsing anything new -
    # reusing the exact same parsed_resume/parsed_jd payloads (as a
    # real client re-clicking "Analyze Again" would).
    second_match_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers,
    )
    assert second_match_resp.status_code == 200
    second_analysis_id = second_match_resp.json()["analysis_id"]
    assert second_analysis_id is not None
    assert second_analysis_id != analysis_id

    session = SessionLocal()
    try:
        counts = _count_rows(session)
        # Resume and job description counts are unchanged - upload was
        # not repeated, neither record was duplicated - but a second,
        # independent analysis now exists alongside the first.
        assert counts == {"resumes": 1, "job_descriptions": 1, "analyses": 2}
    finally:
        session.close()
