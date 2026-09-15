"""Deterministic, regex-based resume text parser.

Each field is extracted by its own small function so any one of them
can be swapped for an NLP/AI-based implementation later without
touching the others. `parse_resume` is the only function other code
should depend on.
"""

import re

from app.schemas.resume import (
    EducationEntry,
    ExperienceEntry,
    ParsedResume,
    ProjectEntry,
)

SECTION_HEADERS: dict[str, list[str]] = {
    "skills": ["skills", "technical skills", "core competencies", "key skills"],
    "education": ["education", "academic background"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
    ],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "languages": ["languages"],
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_CANDIDATE_RE = re.compile(
    r"(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?)?\d{2,4}[ .-]?\d{3,4}[ .-]?\d{0,4}[ .-]?\d{0,4}"
)
DATE_RANGE_RE = re.compile(
    r"\b(?:19|20)\d{2}\b(?:\s*[-–—]\s*(?:\b(?:19|20)\d{2}\b|present|current))?",
    re.IGNORECASE,
)
LOCATION_RE = re.compile(r"^[A-Za-z][A-Za-z.\s]{1,30},\s*[A-Za-z]{2,25}(?:,\s*[A-Za-z]{2,25})?$")
BULLET_RE = re.compile(r"^[•‣◦⁃∙*\-–—•·]\s*")
NAME_SKIP_WORDS = {"resume", "curriculum vitae", "cv"}


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

    contact_lines = lines[: header_positions[0][0]]
    sections: dict[str, list[str]] = {}
    for idx, (start, key) in enumerate(header_positions):
        end = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
        sections.setdefault(key, []).extend(lines[start + 1 : end])

    return contact_lines, sections


def _split_by_blank_lines(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _split_blocks(lines: list[str]) -> list[list[str]]:
    """Split a section's lines into one block per entry.

    PDF text extraction frequently collapses the blank lines that
    originally separated entries, so blank-line splitting alone is
    unreliable. When that yields only a single block, fall back to
    treating a date-range line as the end of an entry's header: the
    line right before it (which has no date of its own) is assumed to
    start a new entry.
    """
    blank_blocks = _split_by_blank_lines(lines)
    if len(blank_blocks) > 1:
        return blank_blocks

    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return []

    boundaries = [0]
    for i in range(1, len(non_empty) - 1):
        if not DATE_RANGE_RE.search(non_empty[i]) and DATE_RANGE_RE.search(non_empty[i + 1]):
            boundaries.append(i)
    boundaries.append(len(non_empty))

    return [non_empty[boundaries[i] : boundaries[i + 1]] for i in range(len(boundaries) - 1)]


def _extract_name(candidate_lines: list[str]) -> str | None:
    for line in candidate_lines[:5]:
        stripped = line.strip()
        if not stripped or "@" in stripped or re.search(r"\d", stripped):
            continue
        if len(stripped.split()) > 5 or stripped.lower() in NAME_SKIP_WORDS:
            continue
        return stripped
    return None


def _extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group() if match else None


def _extract_phone(text: str) -> str | None:
    for match in PHONE_CANDIDATE_RE.finditer(text):
        candidate = match.group().strip(" .-")
        digits = re.sub(r"\D", "", candidate)
        if 9 <= len(digits) <= 15:
            return candidate
    return None


def _extract_location(contact_lines: list[str]) -> str | None:
    for line in contact_lines:
        stripped = line.strip()
        if not stripped or "@" in stripped or "http" in stripped.lower():
            continue
        if LOCATION_RE.match(stripped):
            return stripped
    return None


def _extract_dates(text: str) -> str | None:
    match = DATE_RANGE_RE.search(text)
    return match.group().strip() if match else None


def _split_title_and_org(line: str) -> tuple[str | None, str | None]:
    cleaned = DATE_RANGE_RE.sub("", line).strip(" -|,\t")
    for delimiter in (" | ", " – ", " — ", " - ", ",", " at ", " @ "):
        if delimiter in cleaned:
            left, right = (part.strip() for part in cleaned.split(delimiter, 1))
            if left and right:
                return left, right
    return cleaned or None, None


def _parse_education_block(block: list[str]) -> EducationEntry:
    raw_text = "\n".join(block)
    degree, institution = _split_title_and_org(block[0])
    return EducationEntry(
        institution=institution,
        degree=degree,
        dates=_extract_dates(raw_text),
        raw_text=raw_text,
    )


def _parse_experience_block(block: list[str]) -> ExperienceEntry:
    raw_text = "\n".join(block)
    title, organization = _split_title_and_org(block[0])
    return ExperienceEntry(
        title=title,
        organization=organization,
        dates=_extract_dates(raw_text),
        raw_text=raw_text,
    )


def _parse_project_block(block: list[str]) -> ProjectEntry:
    raw_text = "\n".join(block)
    first_line = block[0]
    for delimiter in (":", " - ", " – ", " — "):
        if delimiter in first_line:
            name, rest = first_line.split(delimiter, 1)
            description = "\n".join([rest.strip(), *block[1:]]).strip()
            return ProjectEntry(name=name.strip() or None, description=description or None, raw_text=raw_text)
    description = "\n".join(block[1:]).strip()
    return ProjectEntry(name=first_line.strip() or None, description=description or None, raw_text=raw_text)


def _split_list_items(lines: list[str]) -> list[str]:
    raw_items = re.split(r"[\n,;•·]+", "\n".join(lines))
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = BULLET_RE.sub("", item).strip(" \t-–—")
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        items.append(cleaned)
    return items


def parse_resume(text: str) -> ParsedResume:
    lines = text.splitlines()
    contact_lines, sections = _find_sections(lines)
    name_search_lines = contact_lines or lines

    return ParsedResume(
        full_name=_extract_name(name_search_lines),
        email=_extract_email(text),
        phone=_extract_phone(text),
        location=_extract_location(contact_lines),
        skills=_split_list_items(sections.get("skills", [])),
        education=[_parse_education_block(b) for b in _split_blocks(sections.get("education", []))],
        work_experience=[
            _parse_experience_block(b) for b in _split_blocks(sections.get("experience", []))
        ],
        projects=[_parse_project_block(b) for b in _split_blocks(sections.get("projects", []))],
        certifications=_split_list_items(sections.get("certifications", [])),
        languages=_split_list_items(sections.get("languages", [])),
    )
