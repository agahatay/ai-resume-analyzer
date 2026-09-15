from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.job_description import ParsedJobDescription
from app.schemas.resume import ParsedResume


def _resume_has_matchable_content(resume: ParsedResume) -> bool:
    return bool(
        resume.skills
        or resume.education
        or resume.work_experience
        or resume.certifications
        or resume.languages
    )


def _job_description_has_matchable_content(job_description: ParsedJobDescription) -> bool:
    return bool(
        job_description.required_skills
        or job_description.preferred_skills
        or job_description.education_requirements
        or job_description.experience_requirements
        or job_description.certifications
        or job_description.languages
    )


class ResumeMatchRequest(BaseModel):
    resume: ParsedResume
    job_description: ParsedJobDescription

    @model_validator(mode="after")
    def check_meaningful_content(self) -> "ResumeMatchRequest":
        # Contact fields (name/email/phone/location) and projects are not used
        # by the matcher, so they don't count toward "has content" here — a
        # resume/JD with only those would still produce a meaningless score.
        errors: list[str] = []
        if not _resume_has_matchable_content(self.resume):
            errors.append(
                "resume contains no matchable data (skills, education, work experience, "
                "certifications, or languages)"
            )
        if not _job_description_has_matchable_content(self.job_description):
            errors.append(
                "job_description contains no matchable requirements (skills, education, "
                "experience, certifications, or languages)"
            )
        if errors:
            raise ValueError("; ".join(errors))
        return self


class EducationMatchResult(BaseModel):
    status: Literal["matched", "partial", "not_matched", "not_specified"]
    details: str


class ExperienceMatchResult(BaseModel):
    status: Literal["matched", "partial", "not_matched", "unknown", "not_specified"]
    details: str
    required_years: float | None = None
    resume_years: float | None = None


class CertificationMatchResult(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class LanguageMatchResult(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ResumeMatchResponse(BaseModel):
    overall_match_score: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    education_match: EducationMatchResult
    experience_match: ExperienceMatchResult
    certification_match: CertificationMatchResult
    language_match: LanguageMatchResult
    summary: str
