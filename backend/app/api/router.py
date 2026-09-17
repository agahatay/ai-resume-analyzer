from fastapi import APIRouter

from app.api import analysis, auth, health, job_description, resume

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(resume.router)
api_router.include_router(job_description.router)
api_router.include_router(analysis.router)
