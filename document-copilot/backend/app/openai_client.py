from openai import AsyncOpenAI, OpenAI

from app.config import settings


def _client_options() -> dict[str, object]:
    return {
        "api_key": settings.openai_api_key,
        # Only set for Azure; None means api.openai.com.
        "base_url": str(settings.openai_base_url) if settings.openai_base_url else None,
        "max_retries": 5,
    }


def create_openai_client() -> OpenAI:
    """Blocking client, for one-off scripts such as ingestion."""
    return OpenAI(**_client_options())  # type: ignore[arg-type]


def create_async_openai_client() -> AsyncOpenAI:
    """Non-blocking client, for request-path code (chat, retrieval)."""
    return AsyncOpenAI(**_client_options())  # type: ignore[arg-type]
