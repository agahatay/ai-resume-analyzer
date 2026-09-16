"""Phase 9C-1: end-to-end tests through the live HTTP API.

Unlike tests/test_resume_repository.py, these go through
POST /api/resume/upload and POST /api/resume/parse via the FastAPI
TestClient, which use the app's own get_db dependency - a real,
committing session on a separate connection from the db_session fixture.
So anything created here is really persisted, and the cleanup_resumes
fixture (see conftest.py) deletes it for real once the test finishes.
"""

from app.core.database import SessionLocal
from app.models.resume import Resume, ResumeEducation, ResumeSkill
from app.services import resume_repository
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


def test_upload_endpoint_creates_resume_row(client, cleanup_resumes):
    pdf_bytes = make_test_pdf_bytes(RESUME_TEXT)

    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "resume_id" in body
    assert body["filename"] == "resume.pdf"
    assert body["character_count"] == len(body["extracted_text"])

    resume_id = body["resume_id"]
    cleanup_resumes.append(resume_id)

    session = SessionLocal()
    try:
        row = session.get(Resume, resume_id)
        assert row is not None
        assert row.original_filename == "resume.pdf"
        assert row.extracted_text == body["extracted_text"]
    finally:
        session.close()


def test_upload_response_still_has_all_original_fields(client, cleanup_resumes):
    pdf_bytes = make_test_pdf_bytes("Just some resume text.")
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    cleanup_resumes.append(body["resume_id"])

    # Every field that existed before Phase 9C-1 must still be present.
    assert set(body.keys()) >= {"filename", "extracted_text", "character_count", "resume_id"}


def test_parse_endpoint_persists_and_links_to_uploaded_resume(client, cleanup_resumes):
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
    )
    assert upload_resp.status_code == 200
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)
    extracted_text = upload_resp.json()["extracted_text"]

    parse_resp = client.post(
        "/api/resume/parse",
        json={"text": extracted_text, "resume_id": resume_id},
    )
    assert parse_resp.status_code == 200
    parsed = parse_resp.json()
    assert parsed["resume_id"] == resume_id
    assert parsed["email"] == "jane.doe@example.com"

    session = SessionLocal()
    try:
        skills = session.query(ResumeSkill).filter_by(resume_id=resume_id).all()
        assert {s.skill for s in skills} == {"Python", "SQL", "FastAPI"}
        education = session.query(ResumeEducation).filter_by(resume_id=resume_id).all()
        assert len(education) == 1
        assert education[0].institution == "MIT"
    finally:
        session.close()


def test_parse_endpoint_without_resume_id_still_persists(client, cleanup_resumes):
    """Backward-compatible path: a client that never called /upload can
    still call /parse directly, as before Phase 9C-1 - it now also gets
    persistence (a fresh Resume row) as a side effect."""
    response = client.post("/api/resume/parse", json={"text": RESUME_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] is not None
    cleanup_resumes.append(body["resume_id"])

    reconstructed = None
    session = SessionLocal()
    try:
        reconstructed = resume_repository.load_parsed_resume(session, body["resume_id"])
    finally:
        session.close()
    assert reconstructed is not None
    assert reconstructed.email == "jane.doe@example.com"


def test_parse_endpoint_repeated_call_does_not_duplicate_rows(client, cleanup_resumes):
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
    )
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)
    extracted_text = upload_resp.json()["extracted_text"]

    for _ in range(2):
        resp = client.post("/api/resume/parse", json={"text": extracted_text, "resume_id": resume_id})
        assert resp.status_code == 200

    session = SessionLocal()
    try:
        skill_count = session.query(ResumeSkill).filter_by(resume_id=resume_id).count()
        assert skill_count == 3  # Python, SQL, FastAPI - not 6
    finally:
        session.close()


def test_parse_endpoint_unknown_resume_id_returns_404(client):
    response = client.post(
        "/api/resume/parse",
        json={"text": "some text", "resume_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
