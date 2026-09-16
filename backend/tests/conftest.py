import uuid

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.main import app
from app.models.resume import Resume


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


def make_test_pdf_bytes(text: str) -> bytes:
    """Build a minimal real PDF (via fpdf2) containing the given text, so
    tests can exercise POST /api/resume/upload's actual text-extraction
    path instead of a blank/placeholder page."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())
