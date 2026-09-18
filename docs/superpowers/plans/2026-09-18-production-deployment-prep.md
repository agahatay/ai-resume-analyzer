# Phase 13B: Production Deployment Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Execution note for this run:** executed inline in the current session rather than dispatched to fresh subagents. The tasks below all touch a small, overlapping set of files (Dockerfiles, compose files, README, CI workflow) and end in one shared verification pass — splitting them across isolated subagents would mean re-deriving the same Docker/Compose context repeatedly for no review benefit. Tasks are still kept as independent, reviewable units.

**Goal:** Prepare (but do not execute) a production deployment: harden the existing Docker/Compose setup, document environment separation and required secrets, add a production Compose file and image-tagging strategy, extend CI with a non-pushing tagged build, and verify nothing in the app itself changed.

**Architecture:** No application code, scoring formulas, or DB schema changes. All work is infra/docs: Dockerfile hardening, a new `docker-compose.prod.yml`, a new `backend/.env.example`-style prod-only example file, README documentation, and one CI workflow tweak (extra image tag, still `push: false`).

**Tech Stack:** Docker / Docker Compose v2, GitHub Actions, FastAPI backend (Python 3.11), Vite/React frontend, nginx (alpine), PostgreSQL 18, Alembic.

**Spec:** Phase 13B instructions in the user's request (this conversation) — no separate spec file exists; the full checklist (sections 1–9) is the spec.

## Global Constraints

- Do NOT deploy to any cloud provider.
- Do NOT create cloud accounts/credentials or add AWS/Azure/GCP infra.
- Do NOT push Docker images to any registry.
- Do NOT change application behavior, scoring formulas, or DB schema.
- Keep the existing CI workflow green.
- Never commit real production secrets — only placeholders (`change_me`, etc.), consistent with existing `.env.example` files.
- Match existing repo conventions: docstring/comment style explaining *why* (see `backend/Dockerfile`'s existing "Phase 12" comments), Compose env-var patterns already in `docker-compose.yml`.

---

### Task 1: Harden the frontend Dockerfile to drop root, tighten dev Compose dependency ordering

**Files:**
- Modify: `frontend/Dockerfile`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: existing multi-stage build (`node:22-alpine` build stage → `nginx:1.27-alpine` production stage), existing `HEALTHCHECK` using `http://127.0.0.1/`.
- Produces: production stage now listens on port 8080 as a non-root user; `docker-compose.yml`'s `frontend.ports` and the frontend `HEALTHCHECK` must be updated to match (8080 instead of 80), and `frontend.depends_on` gains `condition: service_healthy` on `backend`.

**Why:** the current production stage's nginx master process runs as root (the official `nginx:*-alpine` image's default) — the only "non-root execution where practical" gap in the whole Docker setup, since the backend already runs as `appuser`. `nginxinc/nginx-unprivileged` is the standard drop-in replacement: it's the same nginx build pre-configured to run entirely as an unprivileged user on port 8080, needing no extra `chown`/capability juggling.

- [ ] **Step 1: Swap the production stage's base image and port**

Edit `frontend/Dockerfile` production stage:

```dockerfile
# ---- production stage ----
FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

# 127.0.0.1, not localhost: this Alpine image's wget resolves "localhost"
# to ::1 first, and nginx's "listen 8080;" only binds the IPv4 wildcard, so
# "localhost" here caused a false-negative "connection refused".
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget --quiet --spider http://127.0.0.1:8080/ || exit 1
```

(No `USER`/`chown` lines needed — `nginxinc/nginx-unprivileged` already runs as an unprivileged user by default and owns its own runtime directories.)

- [ ] **Step 2: Update `frontend/nginx.conf` to listen on 8080**

Change `listen 80;` to `listen 8080;` in `frontend/nginx.conf`.

- [ ] **Step 3: Update `docker-compose.yml`'s frontend service**

Change the frontend service's port mapping from `"${FRONTEND_PORT:-5173}:80"` to `"${FRONTEND_PORT:-5173}:8080"`, and change `depends_on` from a plain list to a healthy-condition dependency:

```yaml
    depends_on:
      backend:
        condition: service_healthy
```

- [ ] **Step 4: Verify the dev stack still builds and starts healthy**

Run (from repo root, with a root `.env` copied from `.env.example` and filled in — see Task 5):

```bash
docker compose build frontend
docker compose up -d
timeout 90 sh -c 'until docker compose ps frontend | grep -q "healthy"; do sleep 2; done'
docker compose ps
docker compose down -v
```

Expected: `frontend` reports `healthy`; `curl http://localhost:5173` (or the configured `FRONTEND_PORT`) returns the app's `index.html`.

- [ ] **Step 5: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf docker-compose.yml
git commit -m "chore(docker): run frontend nginx as non-root, tighten compose dependency ordering"
```

---

### Task 2: Add `docker-compose.prod.yml`

**Files:**
- Create: `docker-compose.prod.yml`

**Interfaces:**
- Consumes: prebuilt images `ai-resume-analyzer-backend:${IMAGE_TAG:-latest}` / `ai-resume-analyzer-frontend:${IMAGE_TAG:-latest}` (built per Task 3's tagging convention) rather than a `build:` context — production runs published images, it doesn't rebuild from source on the host.
- Produces: a Compose file the user can run locally (still without deploying) via `docker compose -f docker-compose.prod.yml config` / `up` once they've built or pulled the tagged images.

**Why:** the dev `docker-compose.yml` is deliberately kept dev-shaped (`build:` context, Postgres bound to `127.0.0.1:5432` for local `psql`, dev-friendly defaults like `DEBUG=false` but no forced `ENVIRONMENT`). A production Compose file should run named images, force production-safe env values, drop the DB host-port publish entirely, and avoid repeating the healthcheck blocks verbatim — using YAML anchors for the two things that really are identical (the Postgres healthcheck test and the backend env block's non-secret defaults).

- [ ] **Step 1: Write `docker-compose.prod.yml`**

```yaml
# Phase 13B: production-oriented Compose file. Runs prebuilt, tagged images
# (see README's "Image tagging" section) instead of building from source,
# forces production-safe environment values, and never publishes the
# database port to the host. This file is for running the production images
# locally to validate them - it does not deploy anywhere by itself.

x-postgres-healthcheck: &postgres-healthcheck
  test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -d ${DB_NAME:-ai_resume_analyzer}"]
  interval: 5s
  timeout: 5s
  retries: 10
  start_period: 10s

services:
  postgres:
    image: postgres:18
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:-ai_resume_analyzer}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD must be set - see README Secrets section}
    volumes:
      - postgres_data:/var/lib/postgresql
    # No host port published - only the backend service reaches Postgres,
    # over the internal compose network via the "postgres" hostname.
    healthcheck: *postgres-healthcheck

  backend:
    image: ai-resume-analyzer-backend:${IMAGE_TAG:-latest}
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ${DB_NAME:-ai_resume_analyzer}
      DB_USER: ${DB_USER:-postgres}
      DB_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD must be set - see README Secrets section}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:?JWT_SECRET_KEY must be set - see README Secrets section}
      JWT_ALGORITHM: ${JWT_ALGORITHM:-HS256}
      ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
      SEMANTIC_MODEL_NAME: ${SEMANTIC_MODEL_NAME:-sentence-transformers/all-MiniLM-L6-v2}
      SEMANTIC_SIMILARITY_THRESHOLD: ${SEMANTIC_SIMILARITY_THRESHOLD:-0.3}
      CORS_ORIGINS: ${CORS_ORIGINS:?CORS_ORIGINS must be set to the real frontend origin - see README Secrets section}
      ENVIRONMENT: production
      DEBUG: "false"
    volumes:
      - hf_cache:/home/appuser/.cache/huggingface
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  frontend:
    image: ai-resume-analyzer-frontend:${IMAGE_TAG:-latest}
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "${FRONTEND_PORT:-8080}:8080"
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--spider", "http://127.0.0.1:8080/"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

volumes:
  postgres_data:
  hf_cache:
```

Notes for the implementer:
- `VITE_API_BASE_URL` does **not** appear here: it's a Vite *build-time* value baked into the image when it was built (Task 3's build step), not a container-runtime env var, so a Compose `environment:` entry for it here would silently do nothing. This must be documented, not "fixed" with a fake env var.
- `${VAR:?message}` (Compose's required-variable syntax) is used for the three secrets/CORS origin that must never fall back to a dev-safe default in production — `docker compose -f docker-compose.prod.yml config` fails loudly if they're unset, instead of silently booting with `change_me`.

- [ ] **Step 2: Validate the file parses**

Run (from repo root, with the three required vars exported so `config` doesn't fail on the intentional `:?` guards):

```bash
DB_PASSWORD=test JWT_SECRET_KEY=test CORS_ORIGINS=http://example.com docker compose -f docker-compose.prod.yml config
```

Expected: prints the fully resolved config with no errors.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "feat(docker): add production-oriented Compose file"
```

---

### Task 3: Document image tagging strategy and required secrets in README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the tag format used by CI (`ai-resume-analyzer-backend:ci`, extended in Task 4 with `${{ github.sha }}`).
- Produces: a `## Production / Deployment Preparation (Phase 13B)` section other tasks/readers rely on as the canonical doc for env separation, tagging, secrets, and running `docker-compose.prod.yml`.

**Why:** items 2, 3, 5, 6 of the Phase 13B checklist are all documentation deliverables; consolidating them into one new README section (rather than scattering across multiple files) keeps the "one clear responsibility per section" property the existing README already has (`## Docker (Phase 12)`, `## CI (Phase 13A)`).

- [ ] **Step 1: Append the new README section**

Add after the existing `## CI (Phase 13A)` section:

```markdown
## Production / Deployment Preparation (Phase 13B)

Docker images and a production Compose file exist so a real deployment (a future phase) can start from a known-good, already-validated baseline. **Nothing in this section deploys anywhere** - it documents and locally validates what a deployment would use.

### Architecture

Three services, unchanged from the dev stack's shape (see `## Docker (Phase 12)` above): PostgreSQL 18, the FastAPI backend (runs `alembic upgrade head` on every container start, then `uvicorn`), and the React/Vite frontend (built to static files, served by nginx). In production, the backend and frontend are separate images built once and deployed by tag - not rebuilt from source on the host, unlike `docker-compose.yml`'s dev workflow.

### Environment separation

| Environment | Config source | Secrets |
|---|---|---|
| Local dev (host, no Docker) | `backend/.env`, `frontend/.env` (gitignored, copied from `.env.example` files) | Whatever you put in your own `.env` - never committed |
| Local dev (Docker Compose) | repo-root `.env` (gitignored, copied from `.env.example`) | Same - only read by `docker-compose.yml` on your machine |
| CI (GitHub Actions) | Hardcoded/generated inline in `.github/workflows/ci.yml` | `JWT_SECRET_KEY` is generated fresh per run (`openssl rand -hex 32`, never checked in); DB password is a fixed throwaway value for an ephemeral, network-isolated service container |
| Production (future) | Real runtime environment variables / secrets manager (platform-specific - not decided yet, since no cloud provider is chosen in this phase) | Real, unique `DB_PASSWORD` and `JWT_SECRET_KEY`, injected by whatever runs the containers - never a file checked into this repo |

`docker-compose.prod.yml` (below) is the local stand-in for "production config shape" - it has no defaults for secrets and fails to start without them, but you still supply those values yourself, locally, for validation only.

### Image tagging

Tag both images with the git commit SHA (traceable, immutable) and, at release time, a semantic version; `latest` is for human convenience only and should never be the tag a deployment pins to.

```bash
# From the repo root:
SHA=$(git rev-parse --short HEAD)
VERSION=v0.1.0   # bump per your own versioning decisions

docker build -t ai-resume-analyzer-backend:$SHA -t ai-resume-analyzer-backend:$VERSION -t ai-resume-analyzer-backend:latest ./backend
docker build --build-arg VITE_API_BASE_URL=https://api.example.com \
  -t ai-resume-analyzer-frontend:$SHA -t ai-resume-analyzer-frontend:$VERSION -t ai-resume-analyzer-frontend:latest ./frontend
```

No images are pushed to any registry by these commands or by CI (see below) - pushing/publishing is out of scope for this phase.

### Running the production Compose file locally

```bash
copy .env.prod.example .env.prod      # then fill in real-looking local values
docker compose -f docker-compose.prod.yml --env-file .env.prod config   # validate first
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod down     # keeps data
```

- Migrations: identical behavior to dev - `backend`'s entrypoint runs `alembic upgrade head` before `uvicorn` starts, so the schema is always current; there is no separate "migration step" to remember.
- Persistent volumes: `postgres_data` and `hf_cache`, same as dev - only `down -v` removes them.
- Health endpoints: `GET /api/health` (backend liveness) and `GET /api/health/db` (DB connectivity) back both the backend's own `HEALTHCHECK` and `depends_on: condition: service_healthy` for the frontend.
- `docker-compose.prod.yml` never publishes PostgreSQL's port to the host - only `backend` can reach it, over the internal Compose network.

### Secrets and configuration required for a real deployment

Never commit real values for any of these - `.env.prod.example` below only has placeholders, exactly like the existing `.env.example` files.

**Secrets (must be unique, random, and kept out of git):**
- `DB_PASSWORD` - PostgreSQL password.
- `JWT_SECRET_KEY` - signs access tokens; rotating it invalidates every existing session. Generate with `openssl rand -hex 32`.

**Configuration (not secret, but must be set deliberately per environment):**
- `SEMANTIC_MODEL_NAME` - sentence-transformers model id; changing it changes the semantic-matching layer's behavior, so pin it deliberately rather than relying on the code default drifting.
- `SEMANTIC_SIMILARITY_THRESHOLD` - see `backend/app/services/semantic_matcher.py` for how this default was chosen; don't change it without re-validating against real resume/JD pairs.
- `DB_HOST` / `DB_NAME` / `DB_USER` - wherever the production database actually lives; `docker-compose.prod.yml` defaults `DB_HOST` to the Compose service name, which only makes sense if Postgres is co-located in the same Compose project.
- `CORS_ORIGINS` - must be the real frontend origin(s), comma-separated; `docker-compose.prod.yml` has no default and refuses to start without it, since a production backend accepting any/no CORS origin is a real exposure.
- `VITE_API_BASE_URL` - the browser-reachable backend URL, baked into the frontend image at **build time** (see the tagging commands above), not a container-runtime variable - it cannot be changed by editing `docker-compose.prod.yml`'s `environment:`, only by rebuilding the frontend image with a different `--build-arg`.
```

- [ ] **Step 2: Proofread against the actual files**

Re-read `docker-compose.prod.yml` (Task 2) and confirm every env var name and default mentioned in the README matches it exactly (README is describing the file, not the other way around).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document production deployment prep (env separation, tagging, secrets)"
```

---

### Task 4: Add `.env.prod.example` and extend CI with a non-pushing SHA-tagged build

**Files:**
- Create: `.env.prod.example`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the `docker` job's existing backend/frontend `docker/build-push-action@v6` steps (currently tagged only `ai-resume-analyzer-backend:ci` / `ai-resume-analyzer-frontend:ci`, `push: false`).
- Produces: those steps additionally tagged `ai-resume-analyzer-backend:${{ github.sha }}` / `ai-resume-analyzer-frontend:${{ github.sha }}`, still `push: false`, still `load: false` - CI behavior (green/red) unchanged, just an extra tag on images that are built and discarded exactly as before.

**Why:** item 5 (secrets doc) needs a placeholder file to point at from the README (`.env.prod.example`), mirroring the existing root `.env.example` but with production-shaped commentary (no dev fallback framing). Item 7 explicitly asks, as optional, for a CI job that tags with `${{ github.sha }}` without pushing - the existing `docker` job already builds both images, so this is a two-line addition, not a new job.

- [ ] **Step 1: Write `.env.prod.example`**

```bash
# Phase 13B: placeholder for docker-compose.prod.yml's --env-file. Mirrors
# the repo-root .env.example, but every value here is a placeholder for a
# LOCAL VALIDATION run of the production Compose file - never fill this in
# with real production credentials or commit the filled-in version. A real
# deployment injects these as runtime environment variables / secrets from
# whatever platform runs the containers, not from a file in this repo.

DB_NAME=ai_resume_analyzer
DB_USER=postgres
# Required - docker-compose.prod.yml has no fallback default on purpose.
DB_PASSWORD=change_me

# Required - generate with `openssl rand -hex 32`. Rotating it invalidates
# every existing access token.
JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

SEMANTIC_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
SEMANTIC_SIMILARITY_THRESHOLD=0.3

# Required - the real frontend origin(s), comma-separated. No default:
# an open/missing CORS origin is not acceptable in production.
CORS_ORIGINS=https://app.example.com

IMAGE_TAG=latest
BACKEND_PORT=8000
FRONTEND_PORT=8080
```

- [ ] **Step 2: Extend the CI `docker` job's tags**

In `.github/workflows/ci.yml`, change the backend build step's `tags:` from:

```yaml
          tags: ai-resume-analyzer-backend:ci
```
to:
```yaml
          tags: |
            ai-resume-analyzer-backend:ci
            ai-resume-analyzer-backend:${{ github.sha }}
```

and the frontend build step's `tags:` from:

```yaml
          tags: ai-resume-analyzer-frontend:ci
```
to:
```yaml
          tags: |
            ai-resume-analyzer-frontend:ci
            ai-resume-analyzer-frontend:${{ github.sha }}
```

Leave `push: false` and `load: false` untouched on both steps.

- [ ] **Step 3: Confirm `.gitignore` already excludes any filled-in prod env file**

Check `.gitignore`'s existing `.env.*` pattern (already present) covers a hypothetical `.env.prod` - it does, since `.env.prod` matches `.env.*`. No `.gitignore` change needed; note this rather than adding a redundant rule.

- [ ] **Step 4: Commit**

```bash
git add .env.prod.example .github/workflows/ci.yml
git commit -m "ci: tag Docker images with commit SHA (no push); add prod env example"
```

---

### Task 5: Full verification pass

**Files:** none modified - this task only runs checks.

**Interfaces:**
- Consumes: all files from Tasks 1-4.
- Produces: a pass/fail report for every command in Phase 13B item 9, to hand back to the user.

**Why:** the Phase 13B instructions require running the full existing test/build/lint/config-validation suite to prove nothing in application behavior changed, plus validating both Compose files and both production Dockerfiles actually build.

- [ ] **Step 1: Bring up a throwaway local Postgres for backend verification**

No local Postgres is running on this machine outside Docker. Start one standalone container matching `backend/.env`'s existing `DB_NAME`/`DB_USER`/`DB_PASSWORD` (do not reuse the dev Compose project, to avoid clobbering the real dev `postgres_data` volume):

```bash
docker run -d --name arasan-verify-pg -p 127.0.0.1:5432:5432 \
  -e POSTGRES_DB=ai_resume_analyzer -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres123 \
  postgres:18
# wait for it to accept connections, then:
```

- [ ] **Step 2: Backend checks**

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m pytest -v
```

Expected: migrations apply cleanly, `alembic check` reports no drift, full pytest suite passes.

- [ ] **Step 3: Tear down the throwaway Postgres**

```bash
docker rm -f arasan-verify-pg
```

- [ ] **Step 4: Frontend checks**

```bash
cd frontend
npx tsc -b
npm run build
npm run lint
```

- [ ] **Step 5: Playwright E2E**

Requires a live backend + built/previewed frontend, same shape as the CI `e2e` job. Run only if Task 1-4 changes don't affect frontend/backend runtime behavior enough to warrant it (they don't - no app code touched); otherwise reuse the CI job's own steps locally. Record result either way.

- [ ] **Step 6: Compose config validation**

```bash
cd /path/to/repo/root
DB_PASSWORD=x JWT_SECRET_KEY=x docker compose config
DB_PASSWORD=x JWT_SECRET_KEY=x CORS_ORIGINS=http://example.com docker compose -f docker-compose.prod.yml config
```

- [ ] **Step 7: Docker builds**

```bash
docker build -t ai-resume-analyzer-backend:verify ./backend
docker build -t ai-resume-analyzer-frontend:verify ./frontend
```

Expected: both build successfully; frontend image's final stage is `nginxinc/nginx-unprivileged:1.27-alpine`, not root `nginx`.

- [ ] **Step 8: Report results**

Summarize, per Phase 13B item 9's required report shape: production Docker improvements, environment separation, image tagging strategy, security findings, documentation updates, all test results, and anything still required before actual deployment (e.g., choosing a hosting platform/registry, TLS/reverse proxy, real secret storage - explicitly out of scope here).

No commit for this task - it's verification-only. If any check fails, fix the specific file from Tasks 1-4 and re-run only the failing check, then note the fix in that task's own commit rather than amending.

---

## Self-Review Notes

- **Spec coverage:** items 1 (Task 1), 2 (Task 3), 3 (Task 3), 4 (Task 2), 5 (Tasks 3-4), 6 (Task 3), 7 (Task 4), 8 (Task 5 + this plan's own research), 9 (Task 5) are all covered.
- **No placeholders:** every step above has literal file content, not descriptions.
- **Type/name consistency:** `docker-compose.prod.yml` env var names match `docker-compose.yml` and `README.md` exactly; `.env.prod.example` var names match `docker-compose.prod.yml`'s `${VAR}` references exactly.
