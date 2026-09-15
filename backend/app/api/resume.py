from fastapi import APIRouter, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.match import ResumeMatchRequest, ResumeMatchResponse
from app.schemas.resume import ParsedResume, ResumeParseRequest, ResumeUploadResponse
from app.services.pdf_service import (
    EmptyPDFTextError,
    InvalidPDFError,
    extract_text_from_pdf,
)
from app.services.resume_matcher import match_resume_to_job
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/resume", tags=["resume"])

settings = get_settings()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile) -> ResumeUploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a PDF.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a .pdf extension.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > settings.max_resume_upload_size_bytes:
        max_mb = settings.max_resume_upload_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {max_mb:.0f} MB.",
        )

    try:
        extracted_text = extract_text_from_pdf(file_bytes)
    except InvalidPDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyPDFTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ResumeUploadResponse(
        filename=file.filename,
        extracted_text=extracted_text,
        character_count=len(extracted_text),
    )


@router.post("/parse", response_model=ParsedResume)
async def parse_resume_endpoint(payload: ResumeParseRequest) -> ParsedResume:
    try:
        return parse_resume(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume text.",
        ) from exc


@router.post("/match", response_model=ResumeMatchResponse)
async def match_resume_endpoint(payload: ResumeMatchRequest) -> ResumeMatchResponse:
    try:
        return match_resume_to_job(payload.resume, payload.job_description)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match resume against job description.",
        ) from exc
