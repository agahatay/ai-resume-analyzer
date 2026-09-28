---
name: create-migration
description: Use when the user asks to create, generate, or run an Alembic database migration for this project's backend models.
disable-model-invocation: true
---

# Create Migration

Generates and applies an Alembic migration for `backend/app/models/`. User-invoked only (`/create-migration`) — never triggered automatically by Claude, since schema changes touch the real Postgres database.

## Prerequisites

- Run from `backend/` (or `cd` there first).
- `backend/.env` must have working `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` — `alembic.ini` has no `sqlalchemy.url`; `alembic/env.py` builds the connection string at runtime from `app.core.config.Settings`, so a wrong or missing `.env` fails the migration at import time, not silently.
- The target Postgres database must be reachable.

## Steps

1. Ask the user for a short, imperative migration message if not already given (e.g. "add resume_analysis table"), unless the user already supplied one as `$ARGUMENTS`.
2. Generate the migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "<message>"
   ```
3. **Read the generated file** in `backend/alembic/versions/` before applying it. Autogenerate is not always correct — check for:
   - Empty `upgrade()`/`downgrade()` (no model change was actually detected — don't apply a no-op)
   - Dropped columns/tables that shouldn't be dropped (Alembic can't see intent, only schema diffs)
   - Missing `server_default`/`nullable` handling for a new NOT NULL column on a table that may already have rows
4. Apply it:
   ```bash
   alembic upgrade head
   ```
5. Confirm success by checking `alembic current` reports the new revision as head.

## If autogenerate produces nothing

Usually means the model change wasn't imported into `alembic/env.py`'s metadata, or the DB is already in sync. Check `app/models/__init__.py` exports the new/changed model.

## Common mistakes

- Editing a migration file after it's been applied to a shared DB — create a new migration instead.
- Running `alembic upgrade head` without reading the migration first (autogenerate diffs are a starting point, not a guarantee).
