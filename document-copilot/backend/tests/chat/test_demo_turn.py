"""A demo turn: replay a recorded example, refuse anything else, never touch a model."""

import json
from uuid import uuid4

import pytest
import structlog
from structlog.contextvars import merge_contextvars
from structlog.testing import LogCapture

from app.chat import demo_turn
from app.chat.demo_turn import run_demo_turn
from app.demo.examples import CONTACT_URL, notice_text
from tests.fake_demo import FAKE_EXAMPLE, QUESTION, use_fake_example
from tests.fake_supabase import FakeAdmin

pytestmark = pytest.mark.anyio

THREAD = {"id": str(uuid4()), "title": None}


@pytest.fixture(autouse=True)
def fake_examples(monkeypatch):
    use_fake_example(monkeypatch)


@pytest.fixture
def logs():
    capture = LogCapture()
    previous = structlog.get_config()
    structlog.configure(processors=[merge_contextvars, capture])
    yield capture.entries
    structlog.configure(**previous)


async def turn(text, admin=None):
    admin = admin or FakeAdmin()
    out = [e async for e in run_demo_turn(admin, THREAD, text, user_id="u")]
    parsed = [
        e if e == "data: [DONE]\n\n" else json.loads(e.removeprefix("data: "))
        for e in out
    ]
    return parsed, admin


def kinds(parsed):
    return [e["type"] for e in parsed if isinstance(e, dict)]


async def test_an_example_streams_like_a_live_answer_and_is_saved(logs):
    parsed, admin = await turn(QUESTION)
    seen = kinds(parsed)
    assert seen[0] == "start" and seen[-1] == "finish"
    assert seen.index("data-status") < seen.index("text-start")
    assert seen[-3:] == ["text-end", "data-citations", "finish"]
    text = "".join(
        e["delta"] for e in parsed if isinstance(e, dict) and e["type"] == "text-delta"
    )
    assert text == FAKE_EXAMPLE.answer
    assert [m["role"] for m in admin.tables["chat_messages"]] == ["user", "assistant"]
    assert len(admin.tables["message_citations"]) == 1
    done = next(e for e in logs if e["event"] == "turn_finished")
    assert done["outcome"] == "demo_answered" and done["example"] == "fake-apple"


async def test_the_question_is_matched_ignoring_case_and_spacing():
    parsed, _ = await turn("  what was APPLE's   total net sales in fiscal 2024? ")
    assert "text-delta" in kinds(parsed)


async def test_any_other_question_gets_the_notice_and_saves_nothing(logs):
    parsed, admin = await turn("Why did Apple's margins improve?")
    assert parsed[-2] == {"type": "error", "errorText": notice_text()}
    assert parsed[-2]["errorText"].endswith(CONTACT_URL)
    assert "text-delta" not in kinds(parsed)
    assert admin.tables.get("chat_messages", []) == []
    assert (
        next(e for e in logs if e["event"] == "turn_finished")["outcome"]
        == "demo_refused"
    )


async def test_a_failed_save_is_reported_not_hidden():
    admin = FakeAdmin()
    admin.fail_inserts_into = {"chat_messages"}
    parsed, _ = await turn(QUESTION, admin)
    assert "finish" not in kinds(parsed)
    assert parsed[-2]["errorText"] == demo_turn.SAVE_FAILED


async def test_no_ids_are_left_behind_for_the_next_turn():
    await turn(QUESTION)
    assert structlog.contextvars.get_contextvars() == {}
