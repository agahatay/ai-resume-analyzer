# AI Resume Analyzer

## Structure

- `backend/` — FastAPI application
- `frontend/` — React + TypeScript (Vite) application

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

API available at http://localhost:8000, health check at `GET /api/health`.

## Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

App available at http://localhost:5173.

## Docker (Phase 12)

Runs the whole stack - PostgreSQL, backend, frontend - via Docker Compose. Requires Docker Desktop.

```bash
copy .env.example .env      # then fill in DB_PASSWORD and JWT_SECRET_KEY
docker compose build
docker compose up -d
docker compose down          # stop containers, keep data
docker compose down -v       # stop containers AND delete the postgres_data volume - all DB data is lost
```

- Frontend: http://localhost:5173 (nginx serving the Vite production build)
- Backend: http://localhost:8000, health checks at `GET /api/health` and `GET /api/health/db`
- PostgreSQL: bound to `127.0.0.1:5432` on the host for local `psql`/GUI access only; inside Compose, the backend reaches it via the `postgres` service hostname, never `localhost`.
- The backend container runs `alembic upgrade head` on every startup (before uvicorn starts) so the schema is always current - there is no `Base.metadata.create_all()` anywhere.
- The `postgres_data` and `hf_cache` named volumes persist database data and the downloaded sentence-transformers model across `docker compose down` / `up` and restarts. Only `down -v` removes them.
- All secrets (`DB_PASSWORD`, `JWT_SECRET_KEY`) come from your local `.env` (gitignored), never from `docker-compose.yml` or the Dockerfiles.
