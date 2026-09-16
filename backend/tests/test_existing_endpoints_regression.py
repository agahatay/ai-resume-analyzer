"""Baseline regression checks for endpoints that existed before Phase 9A.

No test suite existed prior to this phase; these smoke tests confirm the
app still starts and its pre-existing routes still respond correctly
after wiring in the database module, then real PostgreSQL persistence
(Phase 9C-1/9C-2), and now (Phase 10B) required authentication on
POST /api/resume/upload, POST /api/resume/parse, and
POST /api/job-description/parse. See tests/test_ownership.py for the
dedicated cross-user ownership-enforcement suite.
"""


def test_job_description_parse_endpoint_still_works(client, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post(
        "/api/job-description/parse",
        json={"text": "We need a Python developer with 3 years of experience in FastAPI."},
        headers=headers,
    )
    assert response.status_code == 200
    # Phase 9C-2: this endpoint now persists a JobDescription row as a side
    # effect (see tests/test_job_description_api_persistence.py for
    # dedicated coverage) - clean it up so this regression test stays inert.
    cleanup_job_descriptions.append(response.json()["job_description_id"])


def test_resume_parse_endpoint_still_works(client, cleanup_resumes, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post(
        "/api/resume/parse",
        json={"text": "Experienced software engineer skilled in Python and SQL."},
        headers=headers,
    )
    assert response.status_code == 200
    # Phase 9C-1: this endpoint now persists a Resume row as a side effect
    # (see tests/test_resume_api_persistence.py for dedicated coverage of
    # that behavior) - clean it up so this regression test stays inert.
    cleanup_resumes.append(response.json()["resume_id"])


def test_resume_upload_rejects_non_pdf(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Phase 10B: these three endpoints now require authentication at all
# --------------------------------------------------------------------------


def test_resume_upload_without_auth_returns_401(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 401


def test_resume_parse_without_auth_returns_401(client):
    response = client.post("/api/resume/parse", json={"text": "Some resume text."})
    assert response.status_code == 401


def test_job_description_parse_without_auth_returns_401(client):
    response = client.post("/api/job-description/parse", json={"text": "Some job description text."})
    assert response.status_code == 401


def test_resume_match_without_auth_returns_401(client):
    response = client.post(
        "/api/resume/match",
        json={
            "resume": {"skills": ["Python"]},
            "job_description": {"required_skills": ["Python"]},
        },
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Health and auth endpoints must stay accessible without a token
# --------------------------------------------------------------------------


def test_health_endpoints_remain_accessible_without_auth(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/db").status_code == 200
