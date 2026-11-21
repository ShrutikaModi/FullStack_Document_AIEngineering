import re
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

TITLE_LENGTH = 60
HISTORY_MESSAGES = 6  # the last three question-and-answer pairs
MAX_HISTORY_CHARS = (
    2000  # per earlier message, so one long answer can't crowd out the rest
)

# "[1]" in an old answer points at a passage from an earlier question. Leaving it in would
# invite the model to copy it, so it is removed: old answers give context, never evidence.
OLD_MARKER = re.compile(r"\s?\[\d+\]")


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


def history_for_agent(rows: list[dict[str, Any]]) -> list[ModelMessage]:
    """Turn stored chat rows (oldest first) into the agent's memory of the conversation.

    Text only: saved extras such as the citation payload are left out. The new question is
    not part of `rows`; it is saved only after the turn succeeds.
    """
    history: list[ModelMessage] = []
    for row in rows[-HISTORY_MESSAGES:]:
        text = message_text(row["parts"]).strip()
        if row["role"] == "assistant":
            text = OLD_MARKER.sub("", text)
        if len(text) > MAX_HISTORY_CHARS:
            text = text[:MAX_HISTORY_CHARS] + " ..."
        if not text:
            continue
        if row["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=text)]))
    # The model expects the conversation to open with a user message.
    while history and isinstance(history[0], ModelResponse):
        history.pop(0)
    return history
