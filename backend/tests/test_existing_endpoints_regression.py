"""Baseline regression checks for endpoints that existed before Phase 9A.

No test suite existed prior to this phase; these smoke tests confirm the
app still starts and its pre-existing routes still respond correctly after
wiring in the database module (new imports in app.main -> app.api.health ->
app.core.database -> app.core.config), and, as of Phase 9C-1, after wiring
real PostgreSQL persistence into POST /api/resume/parse and
POST /api/resume/upload.
"""


def test_job_description_parse_endpoint_still_works(client):
    response = client.post(
        "/api/job-description/parse",
        json={"text": "We need a Python developer with 3 years of experience in FastAPI."},
    )
    assert response.status_code == 200


def test_resume_parse_endpoint_still_works(client, cleanup_resumes):
    response = client.post(
        "/api/resume/parse",
        json={"text": "Experienced software engineer skilled in Python and SQL."},
    )
    assert response.status_code == 200
    # Phase 9C-1: this endpoint now persists a Resume row as a side effect
    # (see tests/test_resume_api_persistence.py for dedicated coverage of
    # that behavior) - clean it up so this regression test stays inert.
    cleanup_resumes.append(response.json()["resume_id"])


def test_resume_upload_rejects_non_pdf(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
