"""SQLAlchemy 2.x database infrastructure (Phase 9A).

Provides:
- ``engine``: the process-wide SQLAlchemy engine (psycopg 3 driver).
- ``SessionLocal``: a session factory bound to that engine.
- ``Base``: the declarative base that ORM models (added in later phases)
  will inherit from.
- ``get_db``: a FastAPI dependency that yields a request-scoped session and
  always closes it afterwards.

Creating the engine here does not open a connection immediately -
SQLAlchemy engines are lazy and only connect on first use (e.g. the first
query, or an explicit ``engine.connect()``). This keeps app startup working
even if the database is temporarily unreachable; only requests that
actually touch the database are affected.

Note on ``client_encoding``: ``ai_resume_analyzer`` was originally created
with server encoding ``SQL_ASCII``, under which psycopg 3 returned raw
``bytes`` instead of ``str`` for text results (breaking SQLAlchemy's own
introspection). The database has since been recreated with ``UTF8``
server encoding, which resolves that at the source. The explicit
``client_encoding=utf8`` connect arg is kept here as a harmless, defensive
default - it now simply matches the database's own encoding - so this
comment stays accurate if that ever needs revisiting.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args={"client_encoding": "utf8"},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session.

    Usage: ``db: Session = Depends(get_db)``. The session is always closed
    when the request finishes, even if an exception is raised.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
