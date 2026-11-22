from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth.access import has_full_access
from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.demo_turn import run_demo_turn
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
from app.demo.examples import CONTACT_URL, EXAMPLES, NOTICE_MESSAGE, NOTICE_TITLE

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


class DemoQuestionOut(BaseModel):
    id: str
    company: str
    kind: str
    text: str


class NoticeOut(BaseModel):
    title: str
    message: str
    contact_url: str


class DemoOut(BaseModel):
    # True for accounts that can only use the recorded examples.
    demo: bool
    questions: list[DemoQuestionOut]
    notice: NoticeOut | None


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


@router.get("/demo")
async def demo(user: Current) -> DemoOut:
    """What the screen needs to run in demo mode: the sample questions and the notice."""
    if has_full_access(user):
        return DemoOut(demo=False, questions=[], notice=None)
    return DemoOut(
        demo=True,
        questions=[
            DemoQuestionOut(id=e.id, company=e.company, kind=e.kind, text=e.question)
            for e in EXAMPLES
        ],
        notice=NoticeOut(
            title=NOTICE_TITLE, message=NOTICE_MESSAGE, contact_url=CONTACT_URL
        ),
    )


@router.post("/chat/stream")
async def chat_stream(
    body: StreamRequest, request: Request, user: Current
) -> StreamingResponse:
    admin = request.app.state.supabase_admin
    # Checked before streaming starts, so a bad thread is a clean 403/404.
    thread = await chats.get_owned_thread(admin, body.thread_id, user.id)
    # The one place a question can reach the model: everyone else only gets the recorded
    # examples. Decided here, on the server, from the verified login, so it cannot be skipped
    # by calling the API directly.
    if not has_full_access(user):
        demo_turn = run_demo_turn(
            admin, thread, last_user_text(body.messages), user_id=str(user.id)
        )
        return stream_response(demo_turn)
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
