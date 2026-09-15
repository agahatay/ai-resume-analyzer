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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
