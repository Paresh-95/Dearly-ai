from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str

    openrouter_api_key: str
    embedding_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "nvidia/nemotron-3-embed-1b:free"

    groq_api_key: str
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"

    fish_audio_api_key: str
    fish_audio_base_url: str = "https://api.fish.audio"
    tts_base_url: str = "https://openrouter.ai/api/v1"
    tts_model: str = "fish-audio/s2.1-pro-free:free"

    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"

    deepgram_api_key: str

    frontend_origins: str = "http://localhost:5173"

    minio_endpoint_url: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "rag-grief-storage"
    minio_secure: bool = False

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    auth_cookie_secure: bool = True

    admin_email: str
    admin_password: str

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
