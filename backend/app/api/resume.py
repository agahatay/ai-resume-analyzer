from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.match import ResumeMatchRequest, ResumeMatchResponse
from app.schemas.resume import ParsedResume, ResumeParseRequest, ResumeUploadResponse
from app.services.pdf_service import (
    EmptyPDFTextError,
    InvalidPDFError,
    extract_text_from_pdf,
)
from app.services.analysis_repository import save_analysis_result
from app.services.job_description_repository import get_job_description
from app.services.resume_matcher import match_resume_to_job
from app.services.resume_parser import parse_resume
from app.services.resume_repository import (
    ResumeNotFoundError,
    create_resume,
    get_or_create_resume_for_parse,
    get_resume,
    save_parsed_resume_data,
)

router = APIRouter(prefix="/resume", tags=["resume"])

settings = get_settings()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
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

    try:
        resume = create_resume(
            db, original_filename=file.filename, extracted_text=extracted_text, user_id=current_user.id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the uploaded resume.",
        ) from exc

    return ResumeUploadResponse(
        filename=file.filename,
        extracted_text=extracted_text,
        character_count=len(extracted_text),
        resume_id=resume.id,
    )


@router.post("/parse", response_model=ParsedResume)
async def parse_resume_endpoint(
    payload: ResumeParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParsedResume:
    try:
        parsed = parse_resume(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume text.",
        ) from exc

    # Ownership is derived only from current_user (the verified JWT
    # subject) - payload.resume_id says *which* resume to update, never
    # *whose* it is. get_or_create_resume_for_parse raises
    # ResumeNotFoundError (-> 404 below) both when resume_id doesn't exist
    # and when it belongs to a different user, so a caller can't tell
    # those two cases apart.
    try:
        resume = get_or_create_resume_for_parse(
            db, resume_id=payload.resume_id, text=payload.text, user_id=current_user.id
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve the resume record for this parse.",
        ) from exc

    try:
        save_parsed_resume_data(db, resume, parsed)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parsed resume data.",
        ) from exc

    parsed.resume_id = resume.id
    return parsed


@router.post("/match", response_model=ResumeMatchResponse)
async def match_resume_endpoint(
    payload: ResumeMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeMatchResponse:
    try:
        result = match_resume_to_job(payload.resume, payload.job_description)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match resume against job description.",
        ) from exc

    # Persist this match as a new analysis only when both ids are
    # available. Neither id being present is the normal case for a
    # standalone match call (e.g. pasted resume/JD text with no prior
    # upload or parse) - that existing behavior is preserved unchanged,
    # and no Resume/JobDescription records are invented from a missing
    # id. When ids ARE present, ownership is verified against
    # current_user.id (the verified JWT subject, never anything from the
    # request body) for BOTH the resume and the job description before
    # matching is allowed to persist - a resume_id/job_description_id
    # that exists but belongs to someone else gets the identical 404 a
    # nonexistent id would, so cross-user access can't be distinguished
    # from "not found" by probing.
    resume_id = payload.resume.resume_id
    job_description_id = payload.job_description.job_description_id
    if resume_id is not None and job_description_id is not None:
        resume = get_resume(db, resume_id)
        if resume is None or resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No resume found with id {resume_id}.",
            )
        job_description = get_job_description(db, job_description_id)
        if job_description is None or job_description.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No job description found with id {job_description_id}.",
            )
        try:
            analysis = save_analysis_result(
                db, resume_id=resume_id, job_description_id=job_description_id, match_result=result
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save the analysis result.",
            ) from exc
        result.analysis_id = analysis.id

    return result
