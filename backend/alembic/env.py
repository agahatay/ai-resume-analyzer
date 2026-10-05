from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401 - registers every model on Base.metadata
from app.core.config import get_settings
from app.core.database import Base
from app.core.database import engine as app_engine

# Phase 9B: app.models (imported above, for its side effect of registering
# every table) now populates this metadata with the full application
# schema, so "alembic revision --autogenerate" can see it.
target_metadata = Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Build the DB URL from the app's own Settings (backend/.env) rather than
# from alembic.ini, so the password is never written to a checked-in file.
# Alembic's Config reads this value through ConfigParser, where a bare "%" is
# interpolation syntax. The URL is percent-encoded (see Settings.database_url),
# so every "%" must be doubled to survive that round trip.
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Reuses the app's own engine (app.core.database.engine) rather than
    building a second one from alembic.ini, so migrations always get
    identical connection behavior to the running app (see
    app/core/database.py docstring for the ``client_encoding`` note).
    """
    with app_engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
