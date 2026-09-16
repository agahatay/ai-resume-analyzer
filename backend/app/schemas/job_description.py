import uuid

from pydantic import BaseModel, Field, field_validator

MAX_JOB_DESCRIPTION_LENGTH = 20_000


class ParsedJobDescription(BaseModel):
    job_title: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    # Phase 9C-2: set once the parsed data has been persisted, so the
    # caller knows which JobDescription row to look up or re-parse later.
    job_description_id: uuid.UUID | None = None


class JobDescriptionParseRequest(BaseModel):
    text: str = Field(..., max_length=MAX_JOB_DESCRIPTION_LENGTH)
    # Phase 9C-2: optional link to a JobDescription created by a prior
    # parse call. When given, parsed data is persisted onto that same
    # record (replacing its previous requirements) instead of creating
    # a new one.
    job_description_id: uuid.UUID | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace only")
        return v
