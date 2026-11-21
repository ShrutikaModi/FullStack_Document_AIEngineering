from uuid import uuid4

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse

from app.chat.messages import HISTORY_MESSAGES, MAX_HISTORY_CHARS, history_for_agent
from app.database.chats import recent_messages
from tests.fake_supabase import FakeAdmin


def row(role: str, text: str, extra_parts: list[dict] | None = None) -> dict:
    return {
        "role": role,
        "parts": [{"type": "text", "text": text}, *(extra_parts or [])],
    }


def texts(history) -> list[str]:
    return [part.content for message in history for part in message.parts]


def test_user_rows_become_questions_and_assistant_rows_become_replies_in_order():
    history = history_for_agent(
        [row("user", "Apple iPhone sales?"), row("assistant", "They fell.")]
    )
    assert [type(m) for m in history] == [ModelRequest, ModelResponse]
    assert texts(history) == ["Apple iPhone sales?", "They fell."]


def test_only_the_last_six_messages_are_used():
    rows = [
        row("user" if i % 2 == 0 else "assistant", f"message {i}") for i in range(10)
    ]
    history = history_for_agent(rows)
    assert len(history) == HISTORY_MESSAGES == 6
    assert texts(history)[0] == "message 4" and texts(history)[-1] == "message 9"


def test_old_answers_lose_their_citation_markers():
    history = history_for_agent(
        [
            row("user", "q"),
            row("assistant", "Sales fell 2% [1] to $200 million [2][3]."),
        ]
    )
    assert texts(history)[1] == "Sales fell 2% to $200 million."


def test_user_messages_are_left_untouched():
    history = history_for_agent([row("user", "What does [1] mean?")])
    assert texts(history) == ["What does [1] mean?"]


def test_citation_data_and_other_non_text_parts_are_dropped():
    citations = {
        "type": "data-citations",
        "data": [{"label": 1, "excerpt": "SECRET EXCERPT"}],
    }
    history = history_for_agent(
        [row("user", "q"), row("assistant", "Answer [1].", [citations])]
    )
    assert "SECRET EXCERPT" not in " ".join(texts(history))
    assert texts(history)[1] == "Answer."


def test_a_long_old_message_is_trimmed():
    history = history_for_agent([row("user", "x" * (MAX_HISTORY_CHARS + 500))])
    assert len(texts(history)[0]) == MAX_HISTORY_CHARS + len(" ...")
    assert texts(history)[0].endswith(" ...")


def test_empty_messages_are_skipped():
    history = history_for_agent(
        [row("user", "q"), row("assistant", "   "), row("user", "again")]
    )
    assert texts(history) == ["q", "again"]


def test_history_never_starts_with_an_assistant_reply():
    history = history_for_agent(
        [row("assistant", "orphan"), row("user", "q"), row("assistant", "a")]
    )
    assert isinstance(history[0], ModelRequest)
    assert texts(history) == ["q", "a"]


def test_a_new_thread_has_no_history():
    assert history_for_agent([]) == []


@pytest.mark.anyio
async def test_recent_messages_returns_the_newest_ones_oldest_first():
    admin, thread = FakeAdmin(), uuid4()
    for i in range(5):
        await (
            admin.table("chat_messages")
            .insert(
                {
                    "thread_id": str(thread),
                    "role": "user",
                    "parts": [],
                    "content": f"m{i}",
                }
            )
            .execute()
        )
    await (
        admin.table("chat_messages")
        .insert(
            {
                "thread_id": str(uuid4()),
                "role": "user",
                "parts": [],
                "content": "other thread",
            }
        )
        .execute()
    )

    rows = await recent_messages(admin, thread, 3)
    assert [r["content"] for r in rows] == ["m2", "m3", "m4"]
