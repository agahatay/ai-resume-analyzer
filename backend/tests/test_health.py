"""Regression + Phase 9A coverage for the health endpoints.

These tests do not require a live PostgreSQL connection: the DB-dependent
case is exercised by monkeypatching the SQLAlchemy engine's ``connect``
method, so the suite is deterministic regardless of whether the local
database happens to be reachable when it runs.
"""

from sqlalchemy.exc import OperationalError

from app.api import health as health_module


def test_health_endpoint_ok(client):
    """Pre-existing /api/health endpoint still works (regression)."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_endpoint_reports_connected(client, monkeypatch):
    """/api/health/db returns 200 when the DB query succeeds."""

    class _FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def execute(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(health_module.engine, "connect", lambda: _FakeConnection())

    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_db_endpoint_reports_disconnected(client, monkeypatch):
    """/api/health/db returns 503 (not a 500 crash) when the DB is unreachable."""

    def _raise_connect():
        raise OperationalError("connect", {}, Exception("boom"))

    monkeypatch.setattr(health_module.engine, "connect", _raise_connect)

    response = client.get("/api/health/db")
    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "error", "database": "disconnected"}
    # The error body must never leak connection details or credentials.
    assert "boom" not in response.text
    assert "password" not in response.text.lower()
