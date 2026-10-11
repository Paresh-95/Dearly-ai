from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MC_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://memory:memory@localhost:5433/memory_companion"

    # Auth. The default secret is for local development only; non-development
    # environments refuse to start with it (see `validate_for_environment`).
    jwt_secret: str = "dev-only-insecure-secret-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    refresh_cookie_name: str = "mc_refresh"
    refresh_cookie_secure: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3100"])

    # Embedding dimension is baked into the pgvector column by migration 0001.
    # Changing it requires a new migration plus a full reindex.
    embedding_dim: int = 1536

    # --- Object storage for uploaded originals. "local" (default) needs no setup and is
    # what tests use; "s3" talks to the MinIO container (or any S3-compatible endpoint). ---
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "./data/uploads"
    s3_endpoint_url: str = "http://localhost:9100"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "memory-companion"
    s3_region: str = "us-east-1"

    max_upload_mb: int = 50

    # --- External providers. All optional: leaving them unset is a supported state, not an
    # error — the corresponding ingestion step then fails its job with a clear, honest
    # message instead of fabricating output. See docs/decisions/0003-provider-fallbacks.md ---
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-5-mini"
    openai_stt_model: str = "whisper-1"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Ingestion worker ---
    worker_poll_seconds: float = 2.0
    worker_max_attempts: int = 3

    # --- Memory-aware chunking (Milestone 4). A short memory becomes one chunk; a longer
    # one is split on sentence boundaries so no chunk exceeds this many characters. ---
    chunk_max_chars: int = 1200

    def validate_for_environment(self) -> None:
        if self.environment != "development" and self.jwt_secret.startswith("dev-only"):
            raise RuntimeError("MC_JWT_SECRET must be set outside development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
