from openai import OpenAI

from app.config import settings


def create_openai_client() -> OpenAI:
    """One client for OpenAI or Azure Foundry; base_url is only set for Azure."""
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=str(settings.openai_base_url) if settings.openai_base_url else None,
        max_retries=5,
    )
