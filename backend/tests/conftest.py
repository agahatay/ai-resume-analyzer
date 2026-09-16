import uuid

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.main import app
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.user import User


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db_session():
    """A Session bound to the real PostgreSQL database, scoped to one
    SAVEPOINT-based transaction that is always rolled back at teardown -
    SQLAlchemy's recommended pattern for DB-backed test isolation. Nothing
    a test does through this fixture is ever actually committed.
    """
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def cleanup_resumes():
    """For tests that go through the live HTTP API (TestClient): those
    requests run through the app's own get_db dependency, which opens a
    *separate*, really-committing session/connection from the db_session
    fixture above - so nothing there gets undone by a rollback.

    Yields a list; append any Resume id such a test creates, and this
    fixture deletes it (cascading to all child rows) in a fresh, real,
    committing session once the test finishes, pass or fail.
    """
    created_ids: list[uuid.UUID] = []
    yield created_ids
    if not created_ids:
        return
    session = SessionLocal()
    try:
        for resume_id in created_ids:
            resume = session.get(Resume, resume_id)
            if resume is not None:
                session.delete(resume)
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def cleanup_job_descriptions():
    """Same purpose as cleanup_resumes, for JobDescription rows created by
    tests going through the live HTTP API (POST /api/job-description/parse).
    """
    created_ids: list[uuid.UUID] = []
    yield created_ids
    if not created_ids:
        return
    session = SessionLocal()
    try:
        for job_description_id in created_ids:
            job_description = session.get(JobDescription, job_description_id)
            if job_description is not None:
                session.delete(job_description)
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def cleanup_users():
    """Same purpose as cleanup_resumes, for User rows created by tests
    going through the live HTTP API (POST /api/auth/register)."""
    created_ids: list[uuid.UUID] = []
    yield created_ids
    if not created_ids:
        return
    session = SessionLocal()
    try:
        for user_id in created_ids:
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def auth_headers_factory(client, cleanup_users):
    """Returns a function that registers + logs in a fresh test user via
    the real HTTP endpoints and returns (user_id, headers), where headers
    is a ready-to-use {"Authorization": "Bearer <token>"} dict.

    Callable multiple times per test to get distinct users - needed for
    every cross-user ownership test in tests/test_ownership.py. Each
    registered user is cleaned up via cleanup_users automatically.
    """

    def _make(email: str | None = None, password: str = "s3cur3-password") -> tuple[str, dict[str, str]]:
        email = email or f"test-user-{uuid.uuid4().hex}@example.com"
        register_resp = client.post("/api/auth/register", json={"email": email, "password": password})
        assert register_resp.status_code == 200, register_resp.text
        user_id = register_resp.json()["id"]
        cleanup_users.append(user_id)

        login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]

        return user_id, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def make_db_user(db_session):
    """Creates a real User row directly in the db_session transaction
    (rolled back at teardown, like everything else db_session touches),
    for repository-level tests that need a genuine user_id to satisfy the
    resumes/job_descriptions.user_id foreign key.

    Uses a throwaway, non-Argon2 password_hash string on purpose: these
    tests exercise ownership plumbing, not authentication, so there's no
    need to pay Argon2's real hashing cost for every one of them.
    """

    def _make(email: str | None = None) -> User:
        user = User(
            email=email or f"repo-test-{uuid.uuid4().hex}@example.com",
            password_hash="not-a-real-hash-repository-tests-only",
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _make


def make_test_pdf_bytes(text: str) -> bytes:
    """Build a minimal real PDF (via fpdf2) containing the given text, so
    tests can exercise POST /api/resume/upload's actual text-extraction
    path instead of a blank/placeholder page."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())
