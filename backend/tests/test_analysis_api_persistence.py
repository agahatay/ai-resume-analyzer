"""Phase 9C-3: end-to-end tests through the live HTTP API.

Mirrors tests/test_resume_api_persistence.py and
tests/test_job_description_api_persistence.py: these go through
POST /api/resume/match via the FastAPI TestClient, which uses the app's
own get_db dependency - a real, committing session on a separate
connection from the db_session fixture.

Per Phase 9C-3's instructions, the main happy-path test below uses the
real upload -> parse -> parse(JD) -> match pipeline end to end, with no
mocking of the deterministic or semantic matcher: this is the only way to
prove analysis persistence works against genuine matcher output rather
than a hand-built ResumeMatchResponse (which the repository-level tests
in tests/test_analysis_repository.py already cover in isolation).

Phase 10B: /match now requires authentication, and only ever persists an
analysis when both the resume and the job description belong to the
caller. Cross-user ownership enforcement itself is covered in
tests/test_ownership.py; these tests confirm persistence still works
correctly, exactly as before, for an authorized, single-user caller.

Cleanup: deleting the Resume via cleanup_resumes cascades (ON DELETE
CASCADE) through resume_analyses -> analysis_skill_results /
analysis_summaries, so no separate analysis cleanup fixture is needed.
"""

import uuid

from app.core.database import SessionLocal
from app.models.analysis import AnalysisSkillResult, AnalysisSummary, ResumeAnalysis
from app.services import analysis_repository
from tests.conftest import make_test_pdf_bytes

RESUME_TEXT = (
    "Jane Doe\n"
    "jane.doe@example.com\n"
    "Austin, TX\n"
    "\n"
    "SKILLS\n"
    "Python, SQL, FastAPI\n"
    "\n"
    "EDUCATION\n"
    "BSc Computer Science - MIT\n"
    "2018 - 2022\n"
)

JD_TEXT = (
    "We are looking for a Senior Backend Engineer.\n"
    "\n"
    "Required Skills:\n"
    "Python, SQL, FastAPI\n"
    "\n"
    "Education:\n"
    "Bachelor's degree in Computer Science\n"
)


def _upload_parse_and_match(client, cleanup_resumes, cleanup_job_descriptions, headers):
    """Runs the real end-to-end pipeline: upload a resume, parse it,
    parse a job description, then match them - using the ids the API
    itself returns, exactly as a real client would."""
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)

    parsed_resume_resp = client.post(
        "/api/resume/parse",
        json={"text": upload_resp.json()["extracted_text"], "resume_id": resume_id},
        headers=headers,
    )
    assert parsed_resume_resp.status_code == 200
    parsed_resume = parsed_resume_resp.json()

    parsed_jd_resp = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert parsed_jd_resp.status_code == 200
    parsed_jd = parsed_jd_resp.json()
    cleanup_job_descriptions.append(parsed_jd["job_description_id"])

    match_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers,
    )
    return match_resp, resume_id, parsed_jd["job_description_id"]


def test_match_with_both_ids_creates_analysis_row(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()
    match_resp, resume_id, jd_id = _upload_parse_and_match(client, cleanup_resumes, cleanup_job_descriptions, headers)

    assert match_resp.status_code == 200
    body = match_resp.json()
    assert body["analysis_id"] is not None

    session = SessionLocal()
    try:
        analysis = session.get(ResumeAnalysis, body["analysis_id"])
        assert analysis is not None
        assert str(analysis.resume_id) == resume_id
        assert str(analysis.job_description_id) == jd_id
    finally:
        session.close()


def test_match_analysis_scores_match_api_response_exactly(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()
    match_resp, _resume_id, _jd_id = _upload_parse_and_match(
        client, cleanup_resumes, cleanup_job_descriptions, headers
    )
    body = match_resp.json()

    session = SessionLocal()
    try:
        analysis = session.get(ResumeAnalysis, body["analysis_id"])
        assert analysis.deterministic_score == body["deterministic_match"]["score"]
        assert analysis.semantic_score == body["semantic_match"]["semantic_score"]
        assert analysis.combined_score == body["combined_match_score"]
    finally:
        session.close()


def test_match_analysis_child_rows_persisted(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    match_resp, _resume_id, _jd_id = _upload_parse_and_match(
        client, cleanup_resumes, cleanup_job_descriptions, headers
    )
    body = match_resp.json()
    analysis_id = body["analysis_id"]

    session = SessionLocal()
    try:
        skill_results = session.query(AnalysisSkillResult).filter_by(analysis_id=analysis_id).all()
        assert len(skill_results) == len(body["semantic_match"]["semantic_matches"])

        summary_row = session.query(AnalysisSummary).filter_by(analysis_id=analysis_id).one_or_none()
        assert summary_row is not None
        assert summary_row.summary_text == body["summary"]
    finally:
        session.close()


def test_load_analysis_matches_api_response(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    match_resp, _resume_id, _jd_id = _upload_parse_and_match(
        client, cleanup_resumes, cleanup_job_descriptions, headers
    )
    body = match_resp.json()

    session = SessionLocal()
    try:
        loaded = analysis_repository.load_analysis(session, body["analysis_id"])
    finally:
        session.close()

    assert loaded is not None
    assert loaded.deterministic_score == body["deterministic_match"]["score"]
    assert loaded.semantic_score == body["semantic_match"]["semantic_score"]
    assert loaded.combined_score == body["combined_match_score"]
    assert loaded.summary == body["summary"]


def test_repeated_matching_creates_second_analysis_not_replace(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    user_id, headers = auth_headers_factory()
    first_resp, resume_id, jd_id = _upload_parse_and_match(client, cleanup_resumes, cleanup_job_descriptions, headers)
    assert first_resp.status_code == 200
    first_analysis_id = first_resp.json()["analysis_id"]

    # Re-match the exact same resume/JD pair a second time.
    parsed_resume_resp = client.post(
        "/api/resume/parse", json={"text": RESUME_TEXT, "resume_id": resume_id}, headers=headers
    )
    parsed_jd_resp = client.post(
        "/api/job-description/parse", json={"text": JD_TEXT, "job_description_id": jd_id}, headers=headers
    )
    second_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume_resp.json(), "job_description": parsed_jd_resp.json()},
        headers=headers,
    )
    assert second_resp.status_code == 200
    second_analysis_id = second_resp.json()["analysis_id"]

    assert second_analysis_id != first_analysis_id

    session = SessionLocal()
    try:
        count = (
            session.query(ResumeAnalysis)
            .filter_by(resume_id=resume_id, job_description_id=jd_id)
            .count()
        )
        assert count == 2
        history = analysis_repository.list_analyses_for_resume(session, resume_id, user_id=uuid.UUID(user_id))
        assert [str(a.id) for a in history] == [second_analysis_id, first_analysis_id]
    finally:
        session.close()


def test_match_without_ids_preserves_existing_behavior_and_does_not_persist(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post(
        "/api/resume/match",
        json={
            "resume": {"skills": ["Python", "SQL"]},
            "job_description": {"required_skills": ["Python"], "preferred_skills": ["SQL"]},
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    # Existing behavior unchanged: a full match response, just with no
    # analysis persisted (and therefore no id for one) since neither
    # resume_id nor job_description_id was supplied.
    assert body["analysis_id"] is None
    assert body["overall_match_score"] == 100.0


def test_match_with_unknown_resume_id_returns_404(client, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    parsed_jd_resp = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    jd = parsed_jd_resp.json()
    cleanup_job_descriptions.append(jd["job_description_id"])

    response = client.post(
        "/api/resume/match",
        json={
            "resume": {
                "skills": ["Python"],
                "resume_id": "00000000-0000-0000-0000-000000000000",
            },
            "job_description": jd,
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_match_with_unknown_job_description_id_returns_404(client, cleanup_resumes, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
        headers=headers,
    )
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)
    parsed_resume_resp = client.post(
        "/api/resume/parse",
        json={"text": upload_resp.json()["extracted_text"], "resume_id": resume_id},
        headers=headers,
    )

    response = client.post(
        "/api/resume/match",
        json={
            "resume": parsed_resume_resp.json(),
            "job_description": {
                "required_skills": ["Python"],
                "job_description_id": "00000000-0000-0000-0000-000000000000",
            },
        },
        headers=headers,
    )
    assert response.status_code == 404
