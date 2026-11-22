from pathlib import Path
from typing import Annotated, Literal

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
    # Locally: the direct connection (db.<ref>.supabase.co). Hosted (Vercel connects over
    # IPv4 only, the direct host is IPv6): Supabase's transaction pooler, port 6543.
    # Migrations need a session, so Alembic refuses the transaction pooler (migration_url).
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

    # Accounts (by email) allowed to use the real assistant. Everyone else gets the demo: three
    # recorded examples and no model call, so strangers cannot run up the AI bill. Empty means
    # everyone is in demo mode. Kept in the environment, not in code, so addresses stay out of
    # the repository.
    full_access_emails: Annotated[list[str], NoDecode] = []

    # "console": coloured, readable lines for local work. "json": one JSON object per line,
    # which is what a log search tool (and Railway's log view) can filter by field.
    log_format: Literal["console", "json"] = "console"

    @field_validator("*", mode="before")
    @classmethod
    def reject_placeholders(cls, value: object) -> object:
        if isinstance(value, str) and "your-" in value:
            raise ValueError("still contains a placeholder from .env.example")
        return value

    @field_validator("full_access_emails", mode="before")
    @classmethod
    def split_emails(cls, value: object) -> object:
        if isinstance(value, str):
            return [e.strip().lower() for e in value.split(",") if e.strip()]
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
