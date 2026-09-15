"""Deterministic, regex-based job description parser.

Mirrors the design of `resume_parser.py`: each concern is its own small
function behind a single `parse_job_description` entrypoint, so the
implementation can be swapped for an NLP/AI-based one later without
touching callers. Kept independent from `resume_parser.py` (no shared
imports) so this phase cannot affect the existing resume parsing.
"""

import re

from app.schemas.job_description import ParsedJobDescription

# Headers that introduce skill/requirement bullets we want to keep.
REQUIRED_HEADERS = [
    "required skills",
    "required qualifications",
    "requirements",
    "qualifications",
    "must have",
    "minimum qualifications",
    "technical skills",
    "skills required",
    "skills",
]
PREFERRED_HEADERS = [
    "preferred skills",
    "preferred qualifications",
    "nice to have",
    "nice-to-have",
    "bonus points",
    "pluses",
    "good to have",
]
EDUCATION_HEADERS = ["education", "education requirements", "educational requirements"]
EXPERIENCE_HEADERS = ["experience", "experience requirements", "work experience requirements"]
CERTIFICATION_HEADERS = ["certifications", "certificates", "licenses"]
LANGUAGE_HEADERS = ["languages", "language requirements"]

# Headers that should terminate the previous section but whose content we
# don't extract into any bucket (responsibilities, perks, etc).
IGNORED_HEADERS = [
    "responsibilities",
    "key responsibilities",
    "duties",
    "what you'll do",
    "about the role",
    "about us",
    "about the company",
    "benefits",
    "perks",
    "overview",
    "job description",
    "summary",
    "what we offer",
    "compensation",
    "how to apply",
]

SECTION_HEADERS: dict[str, list[str]] = {
    "required": REQUIRED_HEADERS,
    "preferred": PREFERRED_HEADERS,
    "education": EDUCATION_HEADERS,
    "experience": EXPERIENCE_HEADERS,
    "certifications": CERTIFICATION_HEADERS,
    "languages": LANGUAGE_HEADERS,
    "_ignore": IGNORED_HEADERS,
}

INLINE_LABEL_RE = re.compile(r"^([A-Za-z][A-Za-z\s]{1,40})\s*[:\-]\s*(.+)$")

JOB_TITLE_LABEL_RE = re.compile(r"^(?:job\s*title|position|role|title)\s*[:\-]\s*(.+)$", re.IGNORECASE)
JOB_TITLE_PHRASE_RE = re.compile(
    r"(?:looking for|seeking|hiring)(?:\s+an?)?\s+"
    r"(?:experienced\s+|talented\s+|skilled\s+)?"
    r"([A-Z][A-Za-z0-9+#./ ]{2,60}?)(?:\s+(?:to|who|that|with)\b|[.,]|$)"
)
TITLE_SKIP_PREFIXES = ("we ", "our ", "about ", "at ", "the ")

BULLET_RE = re.compile(r"^[•‣◦⁃∙*\-–—·]\s*")
EXPERIENCE_YEARS_RE = re.compile(r"\b\d{1,2}\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)\b", re.IGNORECASE)
EDUCATION_RE = re.compile(
    r"\b(bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|associate'?s?\s+degree|b\.?s\.?c?\.?|m\.?s\.?c?\.?|degree|diploma)\b",
    re.IGNORECASE,
)
CERTIFICATION_RE = re.compile(r"\bcertifi(?:ed|cation|cate)s?\b", re.IGNORECASE)
LANGUAGE_NAMES = {
    "english", "spanish", "french", "german", "mandarin", "chinese", "japanese",
    "korean", "portuguese", "italian", "russian", "arabic", "hindi", "dutch",
    "turkish", "polish", "vietnamese",
}


def _normalize_header(line: str) -> str:
    cleaned = re.sub(r"[^a-z\s]", " ", line.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    header_lookup = {
        _normalize_header(keyword): key
        for key, keywords in SECTION_HEADERS.items()
        for keyword in keywords
    }

    header_positions: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if len(line.split()) > 5:
            continue
        normalized = _normalize_header(line)
        if normalized in header_lookup:
            header_positions.append((i, header_lookup[normalized]))

    if not header_positions:
        return lines, {}

    preamble_lines = lines[: header_positions[0][0]]
    sections: dict[str, list[str]] = {}
    for idx, (start, key) in enumerate(header_positions):
        end = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
        if key == "_ignore":
            continue
        sections.setdefault(key, []).extend(lines[start + 1 : end])

    return preamble_lines, sections


def _split_section_items(lines: list[str]) -> list[str]:
    """Split a section's lines into individual requirement/skill items.

    Bullet-per-line sections are split on newlines only, so multi-word
    sentences ("5+ years of experience with Python, Django, and Flask")
    stay intact. A section that is really just one comma-separated line
    ("Skills: Python, Django, PostgreSQL") is additionally split on commas.
    """
    raw_lines = [BULLET_RE.sub("", line).strip(" \t-–—") for line in lines]
    raw_lines = [line for line in raw_lines if line]

    if len(raw_lines) == 1 and raw_lines[0].count(",") >= 2:
        raw_lines = [part.strip() for part in raw_lines[0].split(",")]

    items: list[str] = []
    seen: set[str] = set()
    for item in raw_lines:
        if not item or item.lower() in seen:
            continue
        seen.add(item.lower())
        items.append(item)
    return items


def _extract_inline_labeled_items(lines: list[str]) -> dict[str, list[str]]:
    """Catch label+value lines like "Skills: React, TypeScript, CSS" that a
    standalone-header scan misses because the header and its content share
    one line."""
    header_lookup = {
        _normalize_header(keyword): key
        for key, keywords in SECTION_HEADERS.items()
        for keyword in keywords
    }
    results: dict[str, list[str]] = {}
    for line in lines:
        match = INLINE_LABEL_RE.match(line.strip())
        if not match:
            continue
        label, value = match.groups()
        key = header_lookup.get(_normalize_header(label))
        if not key or key == "_ignore":
            continue
        items = [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
        results.setdefault(key, []).extend(items)
    return results


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _extract_job_title(text: str, preamble_lines: list[str]) -> str | None:
    search_lines = preamble_lines[:10] or text.splitlines()[:10]
    for line in search_lines:
        match = JOB_TITLE_LABEL_RE.match(line.strip())
        if match:
            return match.group(1).strip()

    match = JOB_TITLE_PHRASE_RE.search(text)
    if match:
        return match.group(1).strip()

    for line in search_lines[:3]:
        stripped = line.strip()
        if not stripped or len(stripped.split()) > 8:
            continue
        if stripped.lower().startswith(TITLE_SKIP_PREFIXES):
            continue
        return stripped

    return None


def _is_education_item(item: str) -> bool:
    return bool(EDUCATION_RE.search(item))


def _is_experience_item(item: str) -> bool:
    return bool(EXPERIENCE_YEARS_RE.search(item))


def _is_certification_item(item: str) -> bool:
    return bool(CERTIFICATION_RE.search(item))


def _is_language_item(item: str) -> bool:
    words = set(re.findall(r"[a-z]+", item.lower()))
    if "language" in words or "languages" in words:
        return True
    return bool(words & LANGUAGE_NAMES)


def _classify_requirement_items(
    items: list[str],
    default_bucket: list[str],
    education: list[str],
    experience: list[str],
    certifications: list[str],
    languages: list[str],
) -> None:
    for item in items:
        if _is_education_item(item):
            education.append(item)
        elif _is_experience_item(item):
            experience.append(item)
        elif _is_certification_item(item):
            certifications.append(item)
        elif _is_language_item(item):
            languages.append(item)
        else:
            default_bucket.append(item)


def parse_job_description(text: str) -> ParsedJobDescription:
    lines = text.splitlines()
    preamble_lines, sections = _find_sections(lines)
    inline_labeled = _extract_inline_labeled_items(lines)

    required_skills: list[str] = []
    preferred_skills: list[str] = []
    education_requirements: list[str] = []
    experience_requirements: list[str] = []
    certifications: list[str] = []
    languages: list[str] = []

    _classify_requirement_items(
        _split_section_items(sections.get("required", [])) + inline_labeled.get("required", []),
        required_skills,
        education_requirements,
        experience_requirements,
        certifications,
        languages,
    )
    _classify_requirement_items(
        _split_section_items(sections.get("preferred", [])) + inline_labeled.get("preferred", []),
        preferred_skills,
        education_requirements,
        experience_requirements,
        certifications,
        languages,
    )

    education_requirements.extend(_split_section_items(sections.get("education", [])))
    education_requirements.extend(inline_labeled.get("education", []))
    experience_requirements.extend(_split_section_items(sections.get("experience", [])))
    experience_requirements.extend(inline_labeled.get("experience", []))
    certifications.extend(_split_section_items(sections.get("certifications", [])))
    certifications.extend(inline_labeled.get("certifications", []))
    languages.extend(_split_section_items(sections.get("languages", [])))
    languages.extend(inline_labeled.get("languages", []))

    return ParsedJobDescription(
        job_title=_extract_job_title(text, preamble_lines),
        required_skills=_dedupe(required_skills),
        preferred_skills=_dedupe(preferred_skills),
        education_requirements=_dedupe(education_requirements),
        experience_requirements=_dedupe(experience_requirements),
        certifications=_dedupe(certifications),
        languages=_dedupe(languages),
    )
