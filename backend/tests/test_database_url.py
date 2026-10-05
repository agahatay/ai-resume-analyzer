"""Unit coverage for how Settings builds the PostgreSQL connection URL.

A password with URL-reserved characters must survive the trip through
Settings.database_url and SQLAlchemy's make_url unchanged, and must also
survive Alembic's ConfigParser round trip (alembic/env.py doubles "%").
These tests need no live database.
"""

from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import Settings

# Reserved URL characters (@ : / # ?) plus a space, as one password.
TRICKY_PASSWORD = "p@ss:w/rd#1? x"


def _settings(password: str = TRICKY_PASSWORD) -> Settings:
    return Settings(db_user="app user", db_password=password, db_host="db.example", db_port=5433, db_name="resumes")


def test_database_url_parses_back_the_exact_password():
    parsed = make_url(_settings().database_url)

    assert parsed.password == TRICKY_PASSWORD
    assert parsed.username == "app user"
    assert parsed.host == "db.example"
    assert parsed.port == 5433
    assert parsed.database == "resumes"


def test_database_url_carries_sslmode_after_encoding():
    url = _settings().database_url

    assert url.endswith("?sslmode=prefer")
    assert make_url(url).query == {"sslmode": "prefer"}


def test_alembic_config_round_trip_keeps_the_encoded_password():
    # env.py passes the URL through ConfigParser, which treats a bare "%" as
    # interpolation syntax. Doubling it must give back the same URL.
    url = _settings().database_url
    config = Config()
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    round_tripped = config.get_main_option("sqlalchemy.url")

    assert round_tripped == url
    assert make_url(round_tripped).password == TRICKY_PASSWORD
