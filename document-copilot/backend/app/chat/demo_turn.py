"""A chat turn for demo accounts: replay a recorded example, never call a model.

Same stream the real assistant produces (progress lines, answer text, sources), so the screen
behaves identically. Any question that is not one of the examples gets the notice and nothing
is saved. Nothing here can reach the model or the database search: it has no agent or
retriever to call.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

import structlog
from supabase import AsyncClient

from app.chat.orchestrator import SAVE_FAILED, save_answered_turn
from app.chat.streaming import DONE, citations_event, event, status_event, text_pieces
from app.database.chats import Row
from app.demo.examples import find_example, notice_text

log = structlog.get_logger()

# Short pauses so the progress lines and the answer appear the way a live answer does.
STEP_PAUSE_SECONDS = 0.7
PIECE_PAUSE_SECONDS = 0.02


async def run_demo_turn(
    admin: AsyncClient, thread: Row, user_text: str, *, user_id: str
) -> AsyncIterator[str]:
    started = perf_counter()
    message_id = str(uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=message_id, thread_id=str(thread["id"]), user_id=user_id
    )
    outcome = "client_disconnected"
    example = find_example(user_text)
    log.info("turn_started", question_chars=len(user_text), mode="demo")
    try:
        yield event({"type": "start", "messageId": message_id})
        if example is None:
            outcome = "demo_refused"
            yield event({"type": "error", "errorText": notice_text()})
            yield DONE
            return

        asked_at = datetime.now(UTC)
        for step in example.steps:
            yield status_event(step)
            await asyncio.sleep(STEP_PAUSE_SECONDS)
        text_id = str(uuid4())
        yield event({"type": "text-start", "id": text_id})
        for piece in text_pieces(example.answer):
            yield event({"type": "text-delta", "id": text_id, "delta": piece})
            await asyncio.sleep(PIECE_PAUSE_SECONDS)
        yield event({"type": "text-end", "id": text_id})
        yield citations_event(example.sources)

        try:
            await save_answered_turn(
                admin,
                thread,
                user_text,
                message_id,
                asked_at,
                example.answer,
                example.sources,
            )
        except Exception:
            outcome = "save_failed"
            log.exception("could not save chat turn")
            yield event({"type": "error", "errorText": SAVE_FAILED})
        else:
            outcome = "demo_answered"
            yield event({"type": "finish"})
        yield DONE
    finally:
        log.info(
            "turn_finished",
            outcome=outcome,
            ms=round((perf_counter() - started) * 1000),
            example=example.id if example else None,
        )
        structlog.contextvars.clear_contextvars()
