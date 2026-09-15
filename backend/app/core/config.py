from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Resume Analyzer"
    environment: str = "development"
    debug: bool = True

    # Comma-separated list of allowed origins for CORS.
    cors_origins: str = "http://localhost:5173"

    # Maximum allowed size for an uploaded resume PDF, in bytes.
    max_resume_upload_size_bytes: int = 5 * 1024 * 1024  # 5 MB

    # Sentence-transformers model used for semantic similarity matching
    # (Phase 6). Loaded once and cached by semantic_matcher.py, not per request.
    semantic_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Cosine similarity (range [-1, 1], but embeddings of real text cluster in
    # [0, 1]) above which two pieces of text are considered a semantic match.
    # See semantic_matcher.py module docstring for how this default was chosen.
    semantic_similarity_threshold: float = 0.3

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
