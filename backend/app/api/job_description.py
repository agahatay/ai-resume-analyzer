from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.job_description import JobDescriptionParseRequest, ParsedJobDescription
from app.services.job_description_parser import parse_job_description
from app.services.job_description_repository import (
    JobDescriptionNotFoundError,
    get_or_create_job_description_for_parse,
    save_parsed_job_description,
)

router = APIRouter(prefix="/job-description", tags=["job-description"])


@router.post("/parse", response_model=ParsedJobDescription)
async def parse_job_description_endpoint(
    payload: JobDescriptionParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParsedJobDescription:
    try:
        parsed = parse_job_description(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job description text.",
        ) from exc

    # Same ownership policy as resume parsing: current_user.id (the
    # verified JWT subject) is the only source of ownership, never
    # anything from the request body. A job_description_id that doesn't
    # exist and one that belongs to someone else raise the identical
    # JobDescriptionNotFoundError (-> 404 below).
    try:
        job_description = get_or_create_job_description_for_parse(
            db, job_description_id=payload.job_description_id, text=payload.text, user_id=current_user.id
        )
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve the job description record for this parse.",
        ) from exc

    try:
        save_parsed_job_description(db, job_description, parsed)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parsed job description data.",
        ) from exc

    parsed.job_description_id = job_description.id
    return parsed
