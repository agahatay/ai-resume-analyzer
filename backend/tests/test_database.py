"""Phase 9A: unit coverage for the database infrastructure module itself
(engine construction, Base, and the get_db dependency), independent of
whether a live PostgreSQL connection is available.
"""

from sqlalchemy.orm import DeclarativeBase, Session

from app.core import database as db_module


def test_engine_uses_psycopg3_driver():
    assert db_module.engine.url.drivername == "postgresql+psycopg"


def test_engine_targets_configured_database():
    url = db_module.engine.url
    assert url.host == "localhost"
    assert url.port == 5432
    assert url.database == "ai_resume_analyzer"


def test_base_is_declarative_base():
    assert issubclass(db_module.Base, DeclarativeBase)


def test_get_db_yields_and_closes_session():
    gen = db_module.get_db()
    session = next(gen)
    assert isinstance(session, Session)

    closed = {"value": False}
    original_close = session.close

    def _tracking_close():
        closed["value"] = True
        original_close()

    session.close = _tracking_close

    # Exhausting the generator runs the `finally: db.close()` block.
    next(gen, None)
    assert closed["value"] is True
