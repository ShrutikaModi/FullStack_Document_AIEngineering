from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Single source of truth for backend environment. Missing values fail at import."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: AnyHttpUrl
    supabase_anon_key: str = Field(min_length=1)
    supabase_service_role_key: str = Field(min_length=1)
    # Direct/session connection (db.<ref>.supabase.co), never the transaction pooler.
    database_url: str = Field(min_length=1)

    openai_api_key: str = Field(min_length=1)
    # Set for Azure / Microsoft Foundry, e.g. https://<resource>.services.ai.azure.com/openai/v1
    # Leave unset to use api.openai.com. On Azure the "model" names below are deployment names.
    openai_base_url: AnyHttpUrl | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # NoDecode: parse the comma-separated env value ourselves instead of as JSON.
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("*", mode="before")
    @classmethod
    def reject_placeholders(cls, value: object) -> object:
        if isinstance(value, str) and "your-" in value:
            raise ValueError("still contains a placeholder from .env.example")
        return value

    @field_validator("database_url")
    @classmethod
    def require_direct_connection(cls, value: str) -> str:
        if "pooler.supabase.com" in value:
            raise ValueError("use the direct connection, not the transaction pooler")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
