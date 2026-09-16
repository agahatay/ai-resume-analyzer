"""Baseline regression checks for endpoints that existed before Phase 9A.

No test suite existed prior to this phase; these smoke tests confirm the
app still starts and its pre-existing routes still respond correctly after
wiring in the database module (new imports in app.main -> app.api.health ->
app.core.database -> app.core.config).
"""


def test_job_description_parse_endpoint_still_works(client):
    response = client.post(
        "/api/job-description/parse",
        json={"text": "We need a Python developer with 3 years of experience in FastAPI."},
    )
    assert response.status_code == 200


def test_resume_parse_endpoint_still_works(client):
    response = client.post(
        "/api/resume/parse",
        json={"text": "Experienced software engineer skilled in Python and SQL."},
    )
    assert response.status_code == 200


def test_resume_upload_rejects_non_pdf(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
