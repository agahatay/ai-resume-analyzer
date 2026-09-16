from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def health_check_db(response: Response) -> dict[str, str]:
    """Verify connectivity to the PostgreSQL database.

    Runs a trivial ``SELECT 1`` against the configured database. Returns
    200 when the query succeeds, or 503 with a generic (credential-free)
    error message if the database is unreachable or rejects the
    connection.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "disconnected"}

    return {"status": "ok", "database": "connected"}
