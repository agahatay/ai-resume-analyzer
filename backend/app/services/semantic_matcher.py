"""Semantic (embedding-based) similarity layer on top of the Phase 5
deterministic matcher.

Uses a pretrained sentence-transformers model (no training/fine-tuning) to
embed resume text and job-description requirements, then compares them with
cosine similarity. This is purely additive: `resume_matcher.py`'s
deterministic logic is untouched, and this module never removes or
overrides anything it computes — see `resume_matcher.match_resume_to_job`
for how the two are combined (70% deterministic / 30% semantic).

Model loading: the SentenceTransformer model is expensive to load (reads
weights from disk/cache, builds the torch graph), so it is loaded at most
once per process and cached in `_MODEL_CACHE`, keyed by model name. Every
call to `compute_semantic_match` reuses the cached instance — the router
never touches model loading directly.

Similarity threshold: `SEMANTIC_SIMILARITY_THRESHOLD` (default 0.3, see
`app/core/config.py`) was chosen empirically against 5 positive and 5
negative example pairs (see the Phase 6 report), not guessed. With
all-MiniLM-L6-v2 cosine similarity on short technical phrases:
  - genuine paraphrases (e.g. "RESTful API development" vs "Built REST
    APIs using ASP.NET Core") scored 0.33-0.71, average 0.54
  - unrelated technical phrases (e.g. "Kubernetes orchestration" vs "Built
    React user interfaces") scored 0.02-0.10, average 0.08
The two clusters are cleanly separated (0.10 to 0.33, no overlap). 0.3 sits
just below the positive cluster's floor — closer to it than to the exact
midpoint (~0.21) — deliberately biasing toward fewer false "semantic match"
positives, since a wrong ✓ is more misleading to a reader than a real match
merely showing a lower similarity number they can still see.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.schemas.job_description import ParsedJobDescription
from app.schemas.match import SemanticMatchItem, SemanticMatchResult
from app.schemas.resume import ParsedResume

_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer once per model name and reuse it. Not an
    lru_cache so the cache is introspectable/clearable in tests if needed."""
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _encode_all(model: SentenceTransformer, texts: list[str]) -> dict[str, np.ndarray]:
    """Embed every distinct, non-blank text in one batched call (rather than
    one `encode()` per comparison) and return a text -> normalized embedding
    map. Embeddings are L2-normalized so a dot product equals cosine
    similarity."""
    unique_texts = _dedupe_preserve([t for t in texts if t and t.strip()])
    if not unique_texts:
        return {}
    embeddings = model.encode(unique_texts, normalize_embeddings=True, convert_to_numpy=True)
    return dict(zip(unique_texts, embeddings))


def _best_match(
    requirement: str,
    candidates: list[str],
    embeddings: dict[str, np.ndarray],
    threshold: float,
) -> tuple[str | None, float, bool]:
    requirement_embedding = embeddings.get(requirement)
    if requirement_embedding is None:
        return None, 0.0, False

    best_text: str | None = None
    best_score = -1.0
    for candidate in candidates:
        candidate_embedding = embeddings.get(candidate)
        if candidate_embedding is None:
            continue
        score = float(np.dot(requirement_embedding, candidate_embedding))
        if score > best_score:
            best_score = score
            best_text = candidate

    if best_text is None:
        return None, 0.0, False

    rounded_score = round(best_score, 4)
    return best_text, rounded_score, rounded_score >= threshold


def compute_semantic_match(resume: ParsedResume, job_description: ParsedJobDescription) -> SemanticMatchResult:
    settings = get_settings()
    model = _get_model(settings.semantic_model_name)
    threshold = settings.semantic_similarity_threshold

    # Skills get the richest candidate pool: a required skill like "REST API
    # development" is rarely a literal entry in a resume's skills list, but
    # is often demonstrated in an experience or project bullet. Searching
    # across all three is what lets semantic matching catch what the
    # deterministic exact/alias skill matcher misses.
    skills_candidates = _dedupe_preserve(
        list(resume.skills)
        + [entry.raw_text for entry in resume.work_experience]
        + [entry.raw_text for entry in resume.projects]
    )
    experience_candidates = [entry.raw_text for entry in resume.work_experience]
    project_candidates = [entry.raw_text for entry in resume.projects]
    education_candidates = [entry.raw_text for entry in resume.education]
    certification_candidates = list(resume.certifications)

    # (category, requirement texts, resume candidate texts)
    categories: list[tuple[str, list[str], list[str]]] = [
        ("skills", job_description.required_skills, skills_candidates),
        ("experience", job_description.experience_requirements, experience_candidates),
        (
            "projects",
            _dedupe_preserve(job_description.required_skills + job_description.preferred_skills),
            project_candidates,
        ),
        ("education", job_description.education_requirements, education_candidates),
        ("certifications", job_description.certifications, certification_candidates),
    ]

    all_texts: list[str] = []
    for _category, requirements, candidates in categories:
        all_texts.extend(requirements)
        all_texts.extend(candidates)
    embeddings = _encode_all(model, all_texts)

    matches: list[SemanticMatchItem] = []
    for category, requirements, candidates in categories:
        for requirement in requirements:
            matched_text, similarity, is_match = _best_match(requirement, candidates, embeddings, threshold)
            matches.append(
                SemanticMatchItem(
                    category=category,  # type: ignore[arg-type]
                    requirement=requirement,
                    matched_resume_text=matched_text,
                    similarity=similarity,
                    matched=is_match,
                )
            )

    # Neutral when nothing was comparable (e.g. a JD that only specifies
    # languages, so none of the 5 semantic categories have any requirements)
    # — mirrors the deterministic matcher's "not_specified" philosophy
    # rather than reporting a misleading 0%.
    semantic_score = round(100 * (sum(item.similarity for item in matches) / len(matches)), 1) if matches else 100.0

    return SemanticMatchResult(
        semantic_score=semantic_score,
        semantic_matches=matches,
        model_name=settings.semantic_model_name,
        similarity_threshold=threshold,
    )
