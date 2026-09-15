from pydantic import BaseModel, Field, field_validator

MAX_RESUME_TEXT_LENGTH = 50_000


class ResumeUploadResponse(BaseModel):
    filename: str
    extracted_text: str
    character_count: int


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


class ResumeParseRequest(BaseModel):
    text: str = Field(..., max_length=MAX_RESUME_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace only")
        return v
