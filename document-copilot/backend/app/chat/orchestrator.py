import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from supabase import AsyncClient

from app.chat.messages import thread_title
from app.chat.streaming import DONE, event
from app.database.chats import Row, save_turn

log = structlog.get_logger()

STUB_REPLY = (
    "This is a placeholder answer. Document search is not connected yet, "
    "so I can't answer questions from the filings."
)
STUB_DELAY_SECONDS = 0.03


async def stub_reply() -> AsyncIterator[str]:
    """Stands in for the real assistant; it is the part later phases replace."""
    for word in STUB_REPLY.split(" "):
        yield word + " "
        await asyncio.sleep(STUB_DELAY_SECONDS)


async def run_turn(
    admin: AsyncClient, thread: Row, user_text: str
) -> AsyncIterator[str]:
    """One chat turn: stream the reply, then save both messages.

    Nothing is saved if the client disconnects mid-stream. If saving fails the
    client gets an error event instead of a "finish".
    """
    asked_at = datetime.now(UTC)
    message_id = str(uuid4())
    text_id = str(uuid4())
    answer = ""

    yield event({"type": "start", "messageId": message_id})
    yield event({"type": "text-start", "id": text_id})
    async for chunk in stub_reply():
        answer += chunk
        yield event({"type": "text-delta", "id": text_id, "delta": chunk})
    yield event({"type": "text-end", "id": text_id})

    answer = answer.strip()
    user_message = {
        "id": str(uuid4()),
        "thread_id": thread["id"],
        "role": "user",
        "content": user_text,
        "parts": [{"type": "text", "text": user_text}],
        "created_at": asked_at.isoformat(),
    }
    assistant_message = {
        "id": message_id,
        "thread_id": thread["id"],
        "role": "assistant",
        "content": answer,
        "parts": [{"type": "text", "text": answer}],
        "created_at": datetime.now(UTC).isoformat(),
    }
    try:
        await save_turn(
            admin, thread, user_message, assistant_message, thread_title(user_text)
        )
    except Exception:
        log.exception("could not save chat turn", thread_id=thread["id"])
        yield event({"type": "error", "errorText": "Could not save this conversation."})
    else:
        yield event({"type": "finish"})
    yield DONE
