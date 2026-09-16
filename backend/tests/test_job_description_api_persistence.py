"""Phase 9C-2: end-to-end tests through the live HTTP API.

Mirrors tests/test_resume_api_persistence.py: these go through
POST /api/job-description/parse via the FastAPI TestClient, which uses
the app's own get_db dependency - a real, committing session on a
separate connection from the db_session fixture. So anything created
here is really persisted, and the cleanup_job_descriptions fixture (see
conftest.py) deletes it for real once the test finishes.

Phase 10B: this endpoint now requires authentication, so every request
below carries a real, freshly-registered test user's bearer token (via
auth_headers_factory - see conftest.py). Cross-user ownership enforcement
itself is covered in tests/test_ownership.py.
"""

from app.core.database import SessionLocal
from app.models.job_description import JobDescription, JobRequirement
from app.services import job_description_repository

JD_TEXT = (
    "We are looking for a Senior Backend Engineer.\n"
    "\n"
    "Required Skills:\n"
    "Python, PostgreSQL, FastAPI\n"
    "\n"
    "Preferred Skills:\n"
    "Docker, Kubernetes\n"
    "\n"
    "Education:\n"
    "Bachelor's degree in Computer Science\n"
    "\n"
    "Experience:\n"
    "5+ years of experience\n"
    "\n"
    "Certifications:\n"
    "AWS Certified Solutions Architect\n"
    "\n"
    "Languages:\n"
    "English\n"
)


def test_parse_endpoint_returns_job_description_id(client, cleanup_job_descriptions, auth_headers_factory):
    user_id, headers = auth_headers_factory()
    response = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["job_description_id"] is not None
    cleanup_job_descriptions.append(body["job_description_id"])

    session = SessionLocal()
    try:
        jd = session.get(JobDescription, body["job_description_id"])
        # Phase 10B: every newly created JobDescription must be owned by
        # the authenticated caller.
        assert str(jd.user_id) == user_id
    finally:
        session.close()


def test_parse_endpoint_response_still_has_all_original_fields(client, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    cleanup_job_descriptions.append(body["job_description_id"])

    assert set(body.keys()) >= {
        "job_title",
        "required_skills",
        "preferred_skills",
        "education_requirements",
        "experience_requirements",
        "certifications",
        "languages",
        "job_description_id",
    }


def test_parse_endpoint_persists_database_rows(client, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert response.status_code == 200
    jd_id = response.json()["job_description_id"]
    cleanup_job_descriptions.append(jd_id)

    session = SessionLocal()
    try:
        jd = session.get(JobDescription, jd_id)
        assert jd is not None
        assert jd.raw_text == JD_TEXT

        required = session.query(JobRequirement).filter_by(job_description_id=jd_id, category="required_skill").all()
        assert {r.requirement for r in required} == {"Python", "PostgreSQL", "FastAPI"}

        certifications = (
            session.query(JobRequirement).filter_by(job_description_id=jd_id, category="certification").all()
        )
        assert [c.requirement for c in certifications] == ["AWS Certified Solutions Architect"]
    finally:
        session.close()


def test_parse_endpoint_reconstruction_matches_response(client, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    jd_id = body["job_description_id"]
    cleanup_job_descriptions.append(jd_id)

    session = SessionLocal()
    try:
        reconstructed = job_description_repository.load_parsed_job_description(session, jd_id)
    finally:
        session.close()

    assert reconstructed is not None
    assert reconstructed.job_title == body["job_title"]
    assert reconstructed.required_skills == body["required_skills"]
    assert reconstructed.preferred_skills == body["preferred_skills"]
    assert reconstructed.education_requirements == body["education_requirements"]
    assert reconstructed.experience_requirements == body["experience_requirements"]
    assert reconstructed.certifications == body["certifications"]
    assert reconstructed.languages == body["languages"]


def test_parse_endpoint_repeated_call_does_not_duplicate_requirements(
    client, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()
    first = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    jd_id = first.json()["job_description_id"]
    cleanup_job_descriptions.append(jd_id)

    session = SessionLocal()
    try:
        baseline_count = session.query(JobRequirement).filter_by(job_description_id=jd_id).count()
    finally:
        session.close()
    assert baseline_count > 0  # sanity check that the first parse actually produced requirements

    second = client.post(
        "/api/job-description/parse", json={"text": JD_TEXT, "job_description_id": jd_id}, headers=headers
    )
    assert second.status_code == 200
    assert second.json()["job_description_id"] == jd_id

    session = SessionLocal()
    try:
        total = session.query(JobRequirement).filter_by(job_description_id=jd_id).count()
        assert total == baseline_count  # unchanged, not doubled
    finally:
        session.close()


def test_parse_endpoint_unknown_job_description_id_returns_404(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post(
        "/api/job-description/parse",
        json={"text": "some text", "job_description_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 404


def test_parse_endpoint_rejects_blank_text(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post("/api/job-description/parse", json={"text": "   "}, headers=headers)
    assert response.status_code == 422


def test_parse_endpoint_rejects_text_over_max_length(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    too_long = "a" * 20_001
    response = client.post("/api/job-description/parse", json={"text": too_long}, headers=headers)
    assert response.status_code == 422
