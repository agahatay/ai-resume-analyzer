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
