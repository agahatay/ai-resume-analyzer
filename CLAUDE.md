# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A resume-vs-job-description matcher: FastAPI backend (`backend/`) + React/TypeScript/Vite frontend (`frontend/`). Users upload a resume PDF and paste a job description; the backend parses both, computes a deterministic keyword-based match plus a semantic (embedding) similarity layer, and persists resumes/job descriptions/analyses per authenticated user.

## Commands

### Backend (`backend/`)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in JWT_SECRET_KEY and DB settings
uvicorn app.main:app --reload
```

- API: http://localhost:8000, health check at `GET /api/health`.
- Run all tests: `pytest` (from `backend/`; config in `pytest.ini` sets `testpaths = tests`).
- Run a single test file: `pytest tests/test_resume_repository.py`.
- Run a single test: `pytest tests/test_resume_repository.py::test_name -v`.
- Tests run against a **real PostgreSQL database** (see `tests/conftest.py`) — there is no mocked/in-memory DB. `db_session`-based tests roll back via a SAVEPOINT; tests that go through `TestClient` (the live HTTP API) commit for real and must clean up explicitly via the `cleanup_resumes` / `cleanup_job_descriptions` / `cleanup_users` fixtures.
- Migrations: `alembic revision --autogenerate -m "message"` then `alembic upgrade head`, run from `backend/`. `alembic.ini` intentionally has no `sqlalchemy.url` — `alembic/env.py` builds it at runtime from `app.core.config.Settings`, so DB credentials never need to be checked in.

### Frontend (`frontend/`)

```bash
copy .env.example .env
npm install
npm run dev        # http://localhost:5173
npm run build       # tsc -b && vite build
npm run lint        # eslint .
npm run test:e2e    # playwright test (see frontend/e2e/)
```

## Architecture

### Backend layering

Strict one-way dependency flow, each layer only calling the one below it:

```
app/api/*.py        FastAPI routers — HTTP concerns only (status codes, request/response
                     shapes). Auth via Depends(get_current_user); DB via Depends(get_db).
app/services/*.py   Business logic + persistence (the "repository" files) + parsers/matchers.
app/models/*.py     SQLAlchemy ORM models.
app/schemas/*.py    Pydantic request/response models.
app/core/*.py       Cross-cutting: config, database engine/session, JWT + password hashing.
```

- `app/main.py` wires CORS and mounts `app.api.router:api_router` (prefix `/api`), which in turn includes each resource's router (`health`, `auth`, `resume`, `job_description`).
- `app/core/config.py`'s `Settings` (pydantic-settings, loads `backend/.env`) is the single source of truth for config; access it via the cached `get_settings()`, never by reading env vars directly. Secrets (`db_password`, `jwt_secret_key`) are typed `SecretStr` so they never leak into logs/tracebacks/repr.
- `app/core/database.py` defines the SQLAlchemy engine/session and the declarative `Base`; `get_db()` is the FastAPI dependency every endpoint uses for a request-scoped session.
- ORM models compose two mixins from `app/models/mixins.py` — `UUIDPrimaryKeyMixin` and `TimestampMixin`/`CreatedAtMixin` — rather than redeclaring `id`/`created_at`/`updated_at` columns per model.

### Auth & ownership model

- JWT auth lives in `app/core/security.py` (pure crypto: Argon2id via `argon2-cffi`, PyJWT HS256 — no DB access) and `app/services/auth_service.py` (DB-touching register/authenticate). `app/api/deps.py:get_current_user` is the shared FastAPI dependency that resolves a `User` from the `Authorization: Bearer` header; nearly every endpoint depends on it.
- `Resume` and `JobDescription` rows carry `user_id`. `ResumeAnalysis` deliberately does **not** have its own `user_id` — ownership is derived through `analysis.resume.user_id` — to avoid a second copy of the same fact drifting out of sync.
- Ownership is always derived from the verified JWT subject (`current_user.id`), never from an id in the request body. A resource that exists but belongs to another user returns the same 404 as a nonexistent one, so ownership can't be probed by id.
- The frontend mirrors this: `frontend/src/services/api.ts` attaches the bearer token to every request via `authHeaders()`, and a 401 response clears the stored token (forcing `AuthGate` to show the login form again) rather than retrying.

### Matching pipeline

- `app/services/resume_parser.py` / `job_description_parser.py` extract structured data (skills, education, experience, certifications, languages) from raw text.
- `app/services/resume_matcher.py` computes a **deterministic**, fully explainable keyword/regex match (skill alias table, degree-level regex, years-of-experience regex, fixed `WEIGHTS` per dimension) — no LLM/AI involved. A dimension the JD doesn't mention scores neutral (doesn't penalize or reward).
- `app/services/semantic_matcher.py` adds an embedding-based layer (sentence-transformers, cosine similarity against an empirically-chosen threshold), loading the model once per process into a module-level cache.
- The two layers are combined 70% deterministic / 30% semantic (`DETERMINISTIC_WEIGHT`/`SEMANTIC_WEIGHT` in `resume_matcher.py`) into `combined_match_score`. The two matchers are kept independent — the semantic layer only reads parser output and never mutates or overrides the deterministic result.
- A match is only persisted as a `ResumeAnalysis` (via `analysis_repository.py`) when both `resume_id` and `job_description_id` are present and owned by the caller; standalone paste-and-match calls with no ids are not persisted.

### Frontend structure

- `src/services/*.ts` — one file per backend resource (`authService`, `resumeService`, `jobDescriptionService`, `matchService`, `healthService`), all built on the shared `apiGet`/`apiPostJson`/`apiPostForm` helpers in `services/api.ts`.
- `src/components/dashboard/` — the post-match results view (score breakdown, per-dimension analysis, recommendations); `src/components/ui/` — generic presentational primitives (Card, Chip, Spinner, etc.); `src/components/layout/` — page chrome.
- `AuthGate` wraps the whole app (`App.tsx`) and gates rendering on presence of a valid access token.

## Conventions

- Backend code has no linter/formatter configured (no ruff/black/flake8 config present) — match the existing style in the file you're editing.
- Docstrings and inline comments frequently explain *why* a decision was made (including references to the project's phased build history, e.g. "Phase 10A") rather than restating what the code does — follow this pattern rather than adding narration comments.
- Every service function that can fail in an endpoint-relevant way raises a specific exception type (e.g. `ResumeNotFoundError`, `InvalidPDFError`, `EmptyPDFTextError`) that the corresponding router catches and translates to a specific HTTP status — avoid raising generic exceptions across the service/API boundary.
