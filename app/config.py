from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    ingest_token: str = Field(default="change-me", alias="INGEST_TOKEN")

    uploads_dir: Path = Field(default=Path("data/uploads"), alias="UPLOADS_DIR")
    chroma_dir: Path = Field(default=Path("data/chroma"), alias="CHROMA_DIR")

    max_chunk_chars: int = Field(default=220, alias="MAX_CHUNK_CHARS")
    max_context_chars: int = Field(default=6000, alias="MAX_CONTEXT_CHARS")
    default_top_k: int = Field(default=6, alias="DEFAULT_TOP_K")
    default_budget_modules: int = Field(default=3, alias="DEFAULT_BUDGET_MODULES")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return settings
