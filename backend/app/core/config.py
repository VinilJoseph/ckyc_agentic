"""Application Configuration & Settings."""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CKYC Marketplace"
    VERSION: str = "0.3.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database (SQLite with aiosqlite for zero-docker local execution)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ckyc.db"
    DB_ECHO: bool = False
    DB_BUSY_TIMEOUT: int = 5000  # ms

    # Security & Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars-long!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "access_token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Local Document Storage
    STORAGE_DIR: str = "data/storage"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]

    INVITATION_TOKEN_EXPIRE_HOURS: int = 48
    OPENROUTER_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def ensure_data_directories() -> None:
    """Ensure data/ and storage directories exist prior to database/file operations."""
    if "sqlite" in settings.DATABASE_URL and ":memory:" not in settings.DATABASE_URL:
        db_path = settings.DATABASE_URL.split(":///")[-1]
        parent = Path(db_path).parent
        if parent and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    storage_path = Path(settings.STORAGE_DIR)
    if not storage_path.exists():
        storage_path.mkdir(parents=True, exist_ok=True)
