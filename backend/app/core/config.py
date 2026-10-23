from typing import List, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "AI Document Research Assistant"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "doc-assistant-insecure-secret-key-change-in-production-32bytes"
    CSRF_SECRET: str = "doc-assistant-insecure-csrf-key-change-in-production-32bytes"
    SESSION_COOKIE_NAME: str = "doc_assistant_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_assistant"

    # CORS
    CORS_ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Storage & Upload limits
    STORAGE_BACKEND: str = "local"  # "local", "supabase", "mock"
    STORAGE_DIR: str = os.path.join("backend", "storage", "documents")
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: Union[str, List[str]] = [".pdf"]
    ALLOWED_MIME_TYPES: Union[str, List[str]] = ["application/pdf", "application/x-pdf"]

    # Supabase Storage Configuration (Server-Side ONLY)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "documents"
    SUPABASE_STORAGE_TIMEOUT_SECONDS: float = 30.0

    @field_validator("ALLOWED_EXTENSIONS", "ALLOWED_MIME_TYPES", mode="before")
    @classmethod
    def assemble_string_list(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [str(v)]

    # Chunking & Extraction parameters
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    MIN_CHUNK_SIZE: int = 100
    MIN_EXTRACTABLE_TEXT_CHARS: int = 50
    SCANNED_PAGE_MIN_CHARS: int = 15
    RETRIEVAL_TOP_K: int = 6
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.60
    EMBEDDING_DIMENSION: int = 1536

    # AI Providers
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # Optional provider API keys
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

settings = Settings()
