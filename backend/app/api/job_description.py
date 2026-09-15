from fastapi import APIRouter, HTTPException, status

from app.schemas.job_description import JobDescriptionParseRequest, ParsedJobDescription
from app.services.job_description_parser import parse_job_description

router = APIRouter(prefix="/job-description", tags=["job-description"])


@router.post("/parse", response_model=ParsedJobDescription)
async def parse_job_description_endpoint(payload: JobDescriptionParseRequest) -> ParsedJobDescription:
    try:
        return parse_job_description(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job description text.",
        ) from exc
