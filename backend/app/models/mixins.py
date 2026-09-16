"""Shared mixins for ORM models (Phase 9B).

These are small, composable, *non*-declarative base classes so that the
id/timestamp columns that most tables need aren't hand-copied into every
model file. Each concrete model still inherits from
``app.core.database.Base`` directly (mixins come first in the MRO, Base
last), following SQLAlchemy's standard declarative-mixin pattern.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """UUID primary key for top-level entities (Resume, JobDescription,
    ResumeAnalysis).

    Generation happens in two places on purpose:
    - ``default=uuid.uuid4`` supplies the value client-side when inserting
      through the ORM, so the primary key is known immediately without a
      round trip.
    - ``server_default=text("gen_random_uuid()")`` makes the column safe
      (never NULL) even for inserts that bypass the ORM (raw SQL, other
      clients). ``gen_random_uuid()`` is a PostgreSQL built-in since
      version 13 and requires no extension.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class CreatedAtMixin:
    """A single UTC creation timestamp.

    ``DateTime(timezone=True)`` maps to PostgreSQL's ``timestamptz``, which
    always stores the instant in UTC internally regardless of session
    timezone - so this satisfies "use UTC timestamps" without any extra
    conversion code.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TimestampMixin(CreatedAtMixin):
    """created_at + updated_at, both UTC. updated_at is bumped
    automatically on every UPDATE via the ORM (``onupdate``)."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
