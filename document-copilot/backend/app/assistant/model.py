from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings
from app.openai_client import create_async_openai_client


def create_chat_model() -> OpenAIChatModel:
    """The chat model. Uses the same Azure/OpenAI settings as embeddings; on Azure the
    model name is the deployment name (OPENAI_CHAT_MODEL, default gpt-4.1-mini)."""
    return OpenAIChatModel(
        settings.openai_chat_model,
        provider=OpenAIProvider(openai_client=create_async_openai_client()),
    )
