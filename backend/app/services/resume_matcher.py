"""Deterministic, keyword-based matching of a parsed resume against a
parsed job description.

No LLM/AI is used. Every comparison is explainable: skill equivalence is a
static alias table, education/experience use regex-extracted levels/years,
and the overall score is a fixed weighted sum (see `WEIGHTS` below) of
per-dimension sub-scores in [0, 1]. The score is a rough, transparent
keyword-overlap estimate — not a hiring probability.

Kept independent from `resume_parser.py` and `job_description_parser.py`
(only reads their public `LANGUAGE_NAMES` constant) so this phase cannot
break either existing parser.
"""

import re
from datetime import date

from app.schemas.job_description import ParsedJobDescription
from app.schemas.match import (
    CertificationMatchResult,
    DeterministicMatchSummary,
    EducationMatchResult,
    ExperienceMatchResult,
    LanguageMatchResult,
    ResumeMatchResponse,
)
from app.schemas.resume import EducationEntry, ExperienceEntry, ParsedResume
from app.services.job_description_parser import LANGUAGE_NAMES
from app.services.semantic_matcher import compute_semantic_match

# Phase 6: how the deterministic (Phase 5) and semantic scores are combined.
# Required per spec: deterministic outweighs semantic 70/30, since the
# deterministic score is fully explainable while the semantic score is a
# similarity estimate. Must sum to 1.0.
DETERMINISTIC_WEIGHT = 0.7
SEMANTIC_WEIGHT = 0.3
assert abs(DETERMINISTIC_WEIGHT + SEMANTIC_WEIGHT - 1.0) < 1e-9

# Explicit, reproducible weighting of each matching dimension. Required
# skills outweigh preferred skills, per the matching spec. Must sum to 1.0.
WEIGHTS: dict[str, float] = {
    "required_skills": 0.45,
    "preferred_skills": 0.15,
    "education": 0.15,
    "experience": 0.15,
    "certifications": 0.05,
    "languages": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# A dimension the job description doesn't mention at all contributes this
# neutral score rather than penalizing (or rewarding) the candidate for
# something that was never asked for.
NEUTRAL_SCORE = 1.0

# Common skill-name equivalents, normalized (lowercased, punctuation
# stripped) on both sides of the mapping.
SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "reactjs": "react",
    "react": "react",
    "nodejs": "nodejs",
    "node": "nodejs",
    "postgresql": "postgres",
    "postgres": "postgres",
}

DEGREE_LEVEL_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\bph\.?d\.?\b|\bdoctorate\b", re.IGNORECASE), 4),
    (re.compile(r"\bmaster'?s?\b|\bm\.?s\.?c?\.?\b|\bmba\b", re.IGNORECASE), 3),
    (re.compile(r"\bbachelor'?s?\b|\bb\.?s\.?c?\.?\b|\bb\.?a\.?\b", re.IGNORECASE), 2),
    (re.compile(r"\bassociate'?s?\b|\bdiploma\b", re.IGNORECASE), 1),
]

EXPERIENCE_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)", re.IGNORECASE)
DATE_RANGE_RE = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4}|present|current)", re.IGNORECASE)

CERT_STOPWORDS = {
    "is", "a", "an", "the", "plus", "preferred", "required", "certification",
    "certifications", "certificate", "certificates", "or", "and", "equivalent",
}


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _canonical_skill(skill: str) -> str:
    key = _normalize_key(skill)
    return SKILL_ALIASES.get(key, key)


def _extract_skill_tokens(text: str) -> set[str]:
    """Tokenize a skill phrase and canonicalize each token, so both an
    atomic skill entry ("React") and a sentence-style requirement
    ("Strong proficiency in Python and FastAPI") can be matched against."""
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#]*", text)
    return {_canonical_skill(token) for token in raw_tokens if _canonical_skill(token)}


def _match_skills(resume_skills: list[str], job_skills: list[str]) -> tuple[list[str], list[str]]:
    resume_canonical = {_canonical_skill(skill) for skill in resume_skills if skill.strip()}
    matched: list[str] = []
    missing: list[str] = []
    for skill in job_skills:
        if resume_canonical & _extract_skill_tokens(skill):
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing


def _extract_degree_level(text: str) -> int:
    best = 0
    for pattern, level in DEGREE_LEVEL_PATTERNS:
        if pattern.search(text):
            best = max(best, level)
    return best


def _match_education(
    resume_education: list[EducationEntry], job_requirements: list[str]
) -> EducationMatchResult:
    if not job_requirements:
        return EducationMatchResult(
            status="not_specified",
            details="The job description does not specify an education requirement.",
        )

    required_levels = [_extract_degree_level(req) for req in job_requirements]
    required_levels = [level for level in required_levels if level > 0]

    resume_texts = [f"{entry.degree or ''} {entry.raw_text}" for entry in resume_education]
    resume_max_level = max((_extract_degree_level(text) for text in resume_texts), default=0)

    if not required_levels:
        status = "not_specified" if resume_max_level == 0 else "partial"
        details = (
            "The job lists an education requirement that doesn't state a specific degree "
            "level (e.g. 'equivalent practical experience')."
        )
        return EducationMatchResult(status=status, details=details)

    min_required, max_required = min(required_levels), max(required_levels)

    if resume_max_level == 0:
        return EducationMatchResult(
            status="not_matched",
            details="The resume does not list any education matching the required degree level.",
        )
    if resume_max_level >= max_required:
        return EducationMatchResult(
            status="matched",
            details="The resume's highest listed degree meets or exceeds the job's education requirement.",
        )
    if resume_max_level >= min_required:
        return EducationMatchResult(
            status="partial",
            details="The resume meets the minimum education level mentioned, but not the highest one listed.",
        )
    return EducationMatchResult(
        status="not_matched",
        details="The resume's education level is below what the job requires.",
    )


def _extract_required_years(job_requirements: list[str]) -> float | None:
    for requirement in job_requirements:
        match = EXPERIENCE_YEARS_RE.search(requirement)
        if match:
            return float(match.group(1))
    return None


def _extract_resume_years(work_experience: list[ExperienceEntry]) -> float | None:
    current_year = date.today().year
    total_months = 0
    found_any = False
    for entry in work_experience:
        match = DATE_RANGE_RE.search(entry.dates or "")
        if not match:
            continue
        start_year = int(match.group(1))
        end_token = match.group(2).lower()
        end_year = current_year if end_token in ("present", "current") else int(end_token)
        total_months += max((end_year - start_year) * 12, 0)
        found_any = True
    return round(total_months / 12, 1) if found_any else None


def _match_experience(
    resume_work_experience: list[ExperienceEntry], job_requirements: list[str]
) -> ExperienceMatchResult:
    required_years = _extract_required_years(job_requirements)

    if required_years is None:
        status = "not_specified" if not job_requirements else "unknown"
        details = (
            "The job description does not specify a required number of years."
            if status == "not_specified"
            else "The job's experience requirement could not be parsed into a number of years."
        )
        return ExperienceMatchResult(status=status, details=details, required_years=None, resume_years=None)

    resume_years = _extract_resume_years(resume_work_experience)

    if resume_years is None:
        return ExperienceMatchResult(
            status="unknown",
            details=(
                f"The job requires about {required_years:g}+ years of experience, but the resume's "
                "work history does not contain parseable date ranges, so this cannot be determined."
            ),
            required_years=required_years,
            resume_years=None,
        )

    if resume_years >= required_years:
        status = "matched"
        details = f"The resume shows about {resume_years:g} years of experience, meeting the {required_years:g}+ year requirement."
    elif resume_years > 0:
        status = "partial"
        details = f"The resume shows about {resume_years:g} years of experience, below the {required_years:g}+ year requirement."
    else:
        status = "not_matched"
        details = f"The resume shows no usable work history against the {required_years:g}+ year requirement."

    return ExperienceMatchResult(status=status, details=details, required_years=required_years, resume_years=resume_years)


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if word not in CERT_STOPWORDS and len(word) > 2}


def _certs_overlap(resume_cert: str, job_cert: str) -> bool:
    resume_words = _significant_words(resume_cert)
    job_words = _significant_words(job_cert)
    if not resume_words or not job_words:
        return False
    overlap = resume_words & job_words
    return len(overlap) >= min(2, len(resume_words))


def _match_certifications(
    resume_certifications: list[str], job_certifications: list[str]
) -> CertificationMatchResult:
    matched: list[str] = []
    missing: list[str] = []
    for job_cert in job_certifications:
        if any(_certs_overlap(resume_cert, job_cert) for resume_cert in resume_certifications):
            matched.append(job_cert)
        else:
            missing.append(job_cert)
    return CertificationMatchResult(matched=matched, missing=missing)


def _extract_language_names(items: list[str]) -> set[str]:
    names: set[str] = set()
    for item in items:
        words = set(re.findall(r"[a-z]+", item.lower()))
        matched_names = words & LANGUAGE_NAMES
        if matched_names:
            names |= matched_names
        else:
            stripped = item.strip().lower()
            if stripped:
                names.add(stripped)
    return names


def _match_languages(resume_languages: list[str], job_languages: list[str]) -> LanguageMatchResult:
    job_names = _extract_language_names(job_languages)
    resume_names = _extract_language_names(resume_languages)
    matched = sorted(name.capitalize() for name in job_names & resume_names)
    missing = sorted(name.capitalize() for name in job_names - resume_names)
    return LanguageMatchResult(matched=matched, missing=missing)


def _ratio_score(matched_count: int, total_count: int) -> float:
    return matched_count / total_count if total_count > 0 else NEUTRAL_SCORE


_EDUCATION_SCORES = {"matched": 1.0, "partial": 0.5, "not_matched": 0.0, "not_specified": NEUTRAL_SCORE}
_EXPERIENCE_SCORES = {
    "matched": 1.0,
    "partial": 0.5,
    "not_matched": 0.0,
    "unknown": 0.5,
    "not_specified": NEUTRAL_SCORE,
}


def _build_summary(
    matched_skills: list[str],
    missing_required_skills: list[str],
    total_required: int,
    matched_preferred_skills: list[str],
    total_preferred: int,
    education_match: EducationMatchResult,
    experience_match: ExperienceMatchResult,
    certification_match: CertificationMatchResult,
    language_match: LanguageMatchResult,
    overall_score: float,
) -> str:
    parts = [
        f"Matched {len(matched_skills)} of {total_required} required skill(s) and "
        f"{len(matched_preferred_skills)} of {total_preferred} preferred skill(s)."
    ]
    if missing_required_skills:
        parts.append(f"Missing required skills: {', '.join(missing_required_skills)}.")
    parts.append(f"Education: {education_match.status.replace('_', ' ')}.")
    parts.append(f"Experience: {experience_match.status.replace('_', ' ')}.")
    if certification_match.missing:
        parts.append(f"Missing certifications: {', '.join(certification_match.missing)}.")
    if language_match.missing:
        parts.append(f"Missing languages: {', '.join(language_match.missing)}.")
    parts.append(
        f"Overall match score: {overall_score:g}%. This is a deterministic, keyword-based "
        "estimate of resume/job overlap and does not represent an actual hiring probability."
    )
    return " ".join(parts)


def match_resume_to_job(resume: ParsedResume, job_description: ParsedJobDescription) -> ResumeMatchResponse:
    matched_skills, missing_required_skills = _match_skills(resume.skills, job_description.required_skills)
    matched_preferred_skills, missing_preferred_skills = _match_skills(
        resume.skills, job_description.preferred_skills
    )

    education_match = _match_education(resume.education, job_description.education_requirements)
    experience_match = _match_experience(resume.work_experience, job_description.experience_requirements)
    certification_match = _match_certifications(resume.certifications, job_description.certifications)
    language_match = _match_languages(resume.languages, job_description.languages)

    required_score = _ratio_score(len(matched_skills), len(job_description.required_skills))
    preferred_score = _ratio_score(len(matched_preferred_skills), len(job_description.preferred_skills))
    education_score = _EDUCATION_SCORES[education_match.status]
    experience_score = _EXPERIENCE_SCORES[experience_match.status]
    certification_score = _ratio_score(len(certification_match.matched), len(job_description.certifications))
    total_job_languages = len(_extract_language_names(job_description.languages))
    language_score = _ratio_score(len(language_match.matched), total_job_languages)

    overall_score = round(
        100
        * (
            required_score * WEIGHTS["required_skills"]
            + preferred_score * WEIGHTS["preferred_skills"]
            + education_score * WEIGHTS["education"]
            + experience_score * WEIGHTS["experience"]
            + certification_score * WEIGHTS["certifications"]
            + language_score * WEIGHTS["languages"]
        ),
        1,
    )

    summary = _build_summary(
        matched_skills,
        missing_required_skills,
        len(job_description.required_skills),
        matched_preferred_skills,
        len(job_description.preferred_skills),
        education_match,
        experience_match,
        certification_match,
        language_match,
        overall_score,
    )

    # Phase 6: additional semantic similarity layer. Purely additive — none
    # of the deterministic computation above is affected by this call or its
    # result.
    semantic_match = compute_semantic_match(resume, job_description)
    combined_match_score = round(
        DETERMINISTIC_WEIGHT * overall_score + SEMANTIC_WEIGHT * semantic_match.semantic_score, 1
    )

    deterministic_match = DeterministicMatchSummary(
        score=overall_score,
        matched_skills=matched_skills,
        missing_required_skills=missing_required_skills,
        matched_preferred_skills=matched_preferred_skills,
        missing_preferred_skills=missing_preferred_skills,
        education_match=education_match,
        experience_match=experience_match,
        certification_match=certification_match,
        language_match=language_match,
    )

    return ResumeMatchResponse(
        overall_match_score=overall_score,
        matched_skills=matched_skills,
        missing_required_skills=missing_required_skills,
        matched_preferred_skills=matched_preferred_skills,
        missing_preferred_skills=missing_preferred_skills,
        education_match=education_match,
        experience_match=experience_match,
        certification_match=certification_match,
        language_match=language_match,
        summary=summary,
        deterministic_match=deterministic_match,
        semantic_match=semantic_match,
        combined_match_score=combined_match_score,
    )
