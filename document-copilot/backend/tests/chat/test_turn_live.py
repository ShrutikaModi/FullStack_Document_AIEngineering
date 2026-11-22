"""One real turn end to end: real model, real filings, real Supabase tables.

Skipped by default. Run with:  uv run pytest -m integration tests/chat/test_turn_live.py

It creates a throwaway login and thread, asks one question, checks that the answer and its
`message_citations` rows were stored with real chunk ids, then deletes everything it made
(deleting the login removes its profile, threads, messages and citations).
"""

import json
from uuid import UUID, uuid4

import pytest

from app.assistant.agent import build_agent
from app.assistant.model import create_chat_model
from app.auth.dependencies import CurrentUser
from app.chat.messages import HISTORY_MESSAGES, history_for_agent
from app.chat.orchestrator import run_turn
from app.database import chats
from app.database.engine import create_db_engine
from app.database.supabase import create_admin_client
from app.database.users import ensure_profile
from app.openai_client import create_async_openai_client
from app.retrieval.retriever import DocumentRetriever, openai_embedder

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


@pytest.fixture
async def admin():
    client = await create_admin_client()
    yield client


@pytest.fixture
async def temporary_user(admin):
    email = f"eval-{uuid4().hex[:10]}@example.com"
    created = await admin.auth.admin.create_user(
        {"email": email, "password": uuid4().hex, "email_confirm": True}
    )
    user = CurrentUser(
        id=UUID(created.user.id),
        email=email,
        email_confirmed=True,
        access_token="unused",
    )
    await ensure_profile(admin, user)
    yield user
    # Deleting the login cascades to the profile, threads, messages and citations.
    await admin.auth.admin.delete_user(str(user.id))


async def test_a_real_turn_saves_the_answer_and_its_citation_rows(
    admin, temporary_user
):
    engine = create_db_engine()
    try:
        retriever = DocumentRetriever(
            engine, openai_embedder(create_async_openai_client())
        )
        thread = await chats.create_thread(admin, temporary_user.id)
        question = "What was Apple's total net sales in fiscal 2024?"

        events = [
            event
            async for event in run_turn(
                admin,
                thread,
                question,
                agent=build_agent(create_chat_model()),
                retriever=retriever,
                user_id=str(temporary_user.id),
                history=[],
            )
        ]
    finally:
        await engine.dispose()

    parsed = [json.loads(e.removeprefix("data: ")) for e in events if "[DONE]" not in e]
    kinds = [e["type"] for e in parsed]
    assert "error" not in kinds, parsed[-1]
    assert kinds[-1] == "finish"
    assert kinds.index("text-start") > kinds.index("data-status")

    stored = await chats.recent_messages(admin, UUID(thread["id"]), 10)
    assert [m["role"] for m in stored] == ["user", "assistant"]
    assistant = stored[1]
    assert [p["type"] for p in assistant["parts"]] == ["text", "data-citations"]

    rows = (
        await admin.table("message_citations")
        .select("message_id,chunk_id,label")
        .eq("message_id", assistant["id"])
        .execute()
    ).data
    shown = assistant["parts"][1]["data"]["sources"]
    assert rows, "the answer cites sources, so citation rows must exist"
    assert sorted(r["label"] for r in rows) == sorted(s["label"] for s in shown)
    assert {r["chunk_id"] for r in rows} == {s["chunkId"] for s in shown}
    assert all(s["page"] is not None and s["excerpt"] for s in shown)


async def test_a_follow_up_in_a_saved_conversation_remembers_the_company(
    admin, temporary_user
):
    """Two turns through the real database: the first is saved, then reloaded as memory.

    "And what about Services?" names no company, so an answer about Apple can only come
    from the saved first turn (history is read from the database, never the browser).
    """
    engine = create_db_engine()
    try:
        retriever = DocumentRetriever(
            engine, openai_embedder(create_async_openai_client())
        )
        agent = build_agent(create_chat_model())
        thread = await chats.create_thread(admin, temporary_user.id)
        questions = [
            "What was Apple's iPhone revenue in fiscal 2024?",
            "And what about Services?",
        ]
        for question in questions:
            saved = await chats.recent_messages(
                admin, UUID(thread["id"]), HISTORY_MESSAGES
            )
            events = [
                event
                async for event in run_turn(
                    admin,
                    thread,
                    question,
                    agent=agent,
                    retriever=retriever,
                    user_id=str(temporary_user.id),
                    history=history_for_agent(saved),
                )
            ]
            kinds = [
                json.loads(e.removeprefix("data: "))["type"]
                for e in events
                if "[DONE]" not in e
            ]
            assert kinds[-1] == "finish", kinds
            # the thread row the next turn receives must show the stored title
            thread = (
                await admin.table("chat_threads")
                .select("*")
                .eq("id", thread["id"])
                .execute()
            ).data[0]
    finally:
        await engine.dispose()

    stored = await chats.recent_messages(admin, UUID(thread["id"]), 10)
    assert [m["role"] for m in stored] == ["user", "assistant", "user", "assistant"]
    assert thread["title"], "the first question becomes the thread title"
    follow_up = stored[3]
    sources = next(p for p in follow_up["parts"] if p["type"] == "data-citations")[
        "data"
    ]["sources"]
    assert sources and {s["company"] for s in sources} == {"Apple Inc."}
