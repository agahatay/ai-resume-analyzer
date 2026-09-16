import uuid

from pydantic import BaseModel, Field, field_validator

MAX_RESUME_TEXT_LENGTH = 50_000


class ResumeUploadResponse(BaseModel):
    filename: str
    extracted_text: str
    character_count: int
    # Phase 9C-1: the id of the Resume row created in PostgreSQL for this
    # upload. Pass it back on POST /api/resume/parse to persist parsed data
    # against this same resume instead of creating a new one.
    resume_id: uuid.UUID


class EducationEntry(BaseModel):
    institution: str | None = None
    degree: str | None = None
    dates: str | None = None
    raw_text: str


class ExperienceEntry(BaseModel):
    title: str | None = None
    organization: str | None = None
    dates: str | None = None
    raw_text: str


class ProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    raw_text: str


class ParsedResume(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    work_experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    # Phase 9C-1: set on the response once the parsed data has been
    # persisted, so the caller knows which Resume row to look up later.
    # None only if parse_resume() is used directly without going through
    # the persistence layer (e.g. in unit tests of the parser itself).
    resume_id: uuid.UUID | None = None


class ResumeParseRequest(BaseModel):
    text: str = Field(..., max_length=MAX_RESUME_TEXT_LENGTH)
    # Phase 9C-1: optional link to a Resume created by a prior
    # POST /api/resume/upload call. When given, parsed data is persisted
    # onto that same resume (replacing any previous parse's child rows)
    # instead of creating a new one.
    resume_id: uuid.UUID | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace only")
        return v
