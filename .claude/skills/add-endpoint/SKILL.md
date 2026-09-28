---
name: add-endpoint
description: Use when adding a new FastAPI endpoint to this project's backend — scaffolds the router/service/schema/exception layers per the project's strict one-way layering rule.
---

# Add Endpoint

Scaffolds a new backend endpoint following this project's layering rule (`api → services → models/schemas`, one-way) and its per-failure specific-exception convention. See `CLAUDE.md`'s "Backend layering" and "Conventions" sections for the source of these rules.

## The four pieces, in dependency order

1. **Schema** (`app/schemas/<resource>.py`) — Pydantic request/response models. No logic.
2. **Exception** (defined in the service module that raises it, e.g. `app/services/<resource>_repository.py`) — a plain `class FooNotFoundError(Exception): ...`, one per distinct failure the router needs to distinguish. Never raise a bare `Exception`/`ValueError` across the service→API boundary for a case the router needs to handle specifically.
3. **Service function** (`app/services/<resource>_repository.py` or a purpose-named service module) — business logic + persistence. Raises the specific exception(s) on failure. Never imports from `app/api/`. Never constructs an `HTTPException` — that's the router's job.
4. **Router endpoint** (`app/api/<resource>.py`) — HTTP concerns only:
   - `current_user: User = Depends(get_current_user)` for any endpoint touching user-owned data.
   - `db: Session = Depends(get_db)`.
   - Calls the service function, `try/except <SpecificError> as exc: raise HTTPException(status_code=..., detail=str(exc)) from exc` for each specific exception, mapped to the correct status code (404 for not-found, 400/422 for bad input, etc.).
   - Ownership check: derive the owning id from `current_user.id`, **never** from an id in the request body/path. A resource that exists but belongs to another user must raise the same exception (→ same 404) as a nonexistent one — see `get_or_create_resume_for_parse` in `app/services/resume_repository.py` for the canonical pattern.

## Reference implementation to copy from

`app/api/resume.py` (router) + `app/services/resume_repository.py` (service + `ResumeNotFoundError`) is the cleanest existing example of all four pieces together — read both before scaffolding a new endpoint.

## Wiring

- Register the new schema in `app/schemas/__init__.py` if the project re-exports schemas there (check first).
- Include the router in `app/api/router.py` if it's a new resource (new file); if it's a new endpoint on an existing router, just add the `@router.<method>` function to the existing file.

## Common mistakes

- Raising `HTTPException` from inside a `services/*.py` file (breaks the layering rule — services don't know about HTTP).
- Trusting a `resume_id`/`job_description_id` from the request body for ownership instead of re-deriving it from `current_user.id`.
- Catching only the specific exception and forgetting a generic `except Exception` fallback for unexpected failures (existing routers do both — see `upload_resume` in `app/api/resume.py`).
- Persisting a `ResumeAnalysis` with its own `user_id` column — it deliberately has none; ownership is via `analysis.resume.user_id`.
