from functools import lru_cache

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

    def validate_for_environment(self) -> None:
        if self.environment != "development" and self.jwt_secret.startswith("dev-only"):
            raise RuntimeError("MC_JWT_SECRET must be set outside development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
