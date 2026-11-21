from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import (
    HISTORY_MESSAGES,
    UIMessage,
    history_for_agent,
    last_user_text,
    row_to_ui_message,
)
from app.chat.orchestrator import run_turn
from app.chat.streaming import stream_response
from app.database import chats
from app.database.users import ensure_profile

router = APIRouter()

Current = Annotated[CurrentUser, Depends(get_current_user)]


class ThreadOut(BaseModel):
    id: UUID
    title: str | None
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: UUID
    role: str
    parts: list[dict]


class StreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    thread_id: UUID = Field(alias="threadId")
    messages: list[UIMessage] = Field(min_length=1)


@router.get("/threads")
async def list_threads(request: Request, user: Current) -> list[ThreadOut]:
    return await chats.list_threads(request.app.state.supabase_admin, user.id)


@router.post("/threads", status_code=201)
async def create_thread(request: Request, user: Current) -> ThreadOut:
    admin = request.app.state.supabase_admin
    await ensure_profile(admin, user)
    return await chats.create_thread(admin, user.id)


@router.get("/threads/{thread_id}/messages")
async def thread_messages(
    thread_id: UUID, request: Request, user: Current
) -> list[MessageOut]:
    admin = request.app.state.supabase_admin
    await chats.get_owned_thread(admin, thread_id, user.id)
    rows = await chats.list_messages(admin, thread_id)
    return [row_to_ui_message(row) for row in rows]


@router.post("/chat/stream")
async def chat_stream(
    body: StreamRequest, request: Request, user: Current
) -> StreamingResponse:
    admin = request.app.state.supabase_admin
    # Checked before streaming starts, so a bad thread is a clean 403/404.
    thread = await chats.get_owned_thread(admin, body.thread_id, user.id)
    # Memory comes from our own database, never from the browser, so it cannot be forged.
    # It is read before this turn is saved, so it holds only earlier messages.
    recent = await chats.recent_messages(admin, body.thread_id, HISTORY_MESSAGES)
    turn = run_turn(
        admin,
        thread,
        last_user_text(body.messages),
        agent=request.app.state.agent,
        retriever=request.app.state.retriever,
        user_id=str(user.id),
        history=history_for_agent(recent),
    )
    return stream_response(turn)
