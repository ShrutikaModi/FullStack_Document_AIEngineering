from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

TITLE_LENGTH = 60


class UIMessage(BaseModel):
    """A message in the AI SDK wire format. Unknown fields are kept, not rejected."""

    model_config = ConfigDict(extra="allow")

    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[dict[str, Any]]


def message_text(parts: list[dict[str, Any]]) -> str:
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


def last_user_text(messages: list[UIMessage]) -> str:
    """The new question. The client resends the whole conversation; only the last
    message is new, and it must be a non-empty user message."""
    last = messages[-1] if messages else None
    text = message_text(last.parts).strip() if last and last.role == "user" else ""
    if not text:
        raise HTTPException(422, "The last message must be a non-empty user message")
    return text


def thread_title(text: str) -> str:
    one_line = " ".join(text.split())
    return one_line[:TITLE_LENGTH]


def row_to_ui_message(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": row["id"], "role": row["role"], "parts": row["parts"]}
