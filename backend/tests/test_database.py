"""Phase 9A: unit coverage for the database infrastructure module itself
(engine construction, Base, and the get_db dependency), independent of
whether a live PostgreSQL connection is available.
"""

from sqlalchemy.orm import DeclarativeBase, Session

from app.core import database as db_module
from app.core.config import get_settings


def test_engine_uses_psycopg3_driver():
    assert db_module.engine.url.drivername == "postgresql+psycopg"


def test_engine_targets_configured_database():
    # Asserted against the live Settings, not a literal - DB_HOST in
    # particular legitimately differs between running the backend directly
    # on a host (backend/.env) and CI (.github/workflows/ci.yml sets it via
    # env vars), so hardcoding either value here would make the test lie
    # about what it's actually checking in the other environment.
    settings = get_settings()
    url = db_module.engine.url
    assert url.host == settings.db_host
    assert url.port == settings.db_port
    assert url.database == settings.db_name


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
