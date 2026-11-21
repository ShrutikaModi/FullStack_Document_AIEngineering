import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.assistant.agent import build_agent
from app.main import app
from tests.assistant.test_agent import FakeRetriever
from tests.fake_supabase import FakeAdmin

ANSWER = "iPhone net sales were $201,183 million [1]."

ALICE, BOB = str(uuid4()), str(uuid4())
AUTH_ALICE = {"Authorization": "Bearer alice"}
AUTH_BOB = {"Authorization": "Bearer bob"}


def scripted_model(messages, info: AgentInfo) -> ModelResponse:
    """Stands in for the LLM: search once, then answer with a valid citation."""
    already_searched = any(
        type(part).__name__ == "ToolReturnPart" and part.tool_name == "search_filings"
        for message in messages
        for part in message.parts
    )
    if not already_searched:
        args = {"reason": "find sales", "query": "iPhone sales", "tickers": ["AAPL"]}
        return ModelResponse(parts=[ToolCallPart("search_filings", args)])
    answer = {
        "answer": ANSWER,
        "citations": [{"label": 1, "passage_id": "P1"}],
        "enough_evidence": True,
    }
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answer)])


@pytest.fixture
def admin(monkeypatch):
    fake = FakeAdmin()
    fake.add_user("alice", ALICE, "alice@driftwood.com")
    fake.add_user("bob", BOB, "bob@driftwood.com")
    app.state.supabase_admin = fake
    app.state.retriever = FakeRetriever()
    app.state.agent = build_agent(FunctionModel(scripted_model))
    return fake


@pytest.fixture
def client(admin):
    return TestClient(app)


def new_thread(client, headers=AUTH_ALICE) -> str:
    return client.post("/threads", headers=headers).json()["id"]


def ask(client, thread_id, text="What was Apple's revenue?", headers=AUTH_ALICE):
    body = {
        "threadId": thread_id,
        "messages": [
            {"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}
        ],
    }
    return client.post("/chat/stream", json=body, headers=headers)


def events(response) -> list[dict | str]:
    out = []
    for line in response.text.split("\n\n"):
        if line.startswith("data: "):
            data = line.removeprefix("data: ")
            out.append(data if data == "[DONE]" else json.loads(data))
    return out


def test_threads_need_a_login(client):
    assert client.get("/threads").status_code == 401
    assert client.post("/threads").status_code == 401
    assert client.post("/chat/stream", json={}).status_code == 401


def test_create_thread_makes_profile_and_lists_only_mine(client, admin):
    mine = new_thread(client)
    new_thread(client, AUTH_BOB)

    assert admin.tables["users"][0]["email"] == "alice@driftwood.com"
    listed = client.get("/threads", headers=AUTH_ALICE).json()
    assert [t["id"] for t in listed] == [mine]


def test_threads_are_newest_first(client):
    first, second = new_thread(client), new_thread(client)
    ids = [t["id"] for t in client.get("/threads", headers=AUTH_ALICE).json()]
    assert ids == [second, first]


def test_foreign_thread_is_403_and_missing_is_404(client):
    bobs = new_thread(client, AUTH_BOB)
    assert (
        client.get(f"/threads/{bobs}/messages", headers=AUTH_ALICE).status_code == 403
    )
    assert ask(client, bobs).status_code == 403
    missing = str(uuid4())
    assert (
        client.get(f"/threads/{missing}/messages", headers=AUTH_ALICE).status_code
        == 404
    )
    assert ask(client, missing).status_code == 404


def test_stream_has_the_expected_events(client):
    response = ask(client, new_thread(client))
    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert response.headers["content-type"].startswith("text/event-stream")

    parsed = events(response)
    types = [e if isinstance(e, str) else e["type"] for e in parsed]
    # progress first, then (only after the answer is verified) the text, sources, finish
    assert types[0] == "start" and types[1] == "data-status"
    assert types[-4:] == ["text-end", "data-citations", "finish", "[DONE]"]
    assert types.index("text-start") > types.index("data-status")
    deltas = "".join(
        e["delta"] for e in parsed if e != "[DONE]" and e["type"] == "text-delta"
    )
    assert deltas == ANSWER


def test_progress_lines_are_transient_and_say_what_is_searched(client):
    status = [
        e
        for e in events(ask(client, new_thread(client)))
        if e != "[DONE]" and e["type"] == "data-status"
    ]
    assert status[0]["transient"] is True
    assert "AAPL" in status[0]["data"]["text"]
    assert "iPhone sales" in status[0]["data"]["text"]


def test_sources_come_from_our_stored_passage_not_from_the_model(client):
    citations = next(
        e
        for e in events(ask(client, new_thread(client)))
        if e != "[DONE]" and e["type"] == "data-citations"
    )
    (source,) = citations["data"]["sources"]
    assert source["label"] == 1
    assert (source["company"], source["page"], source["fiscalYear"]) == (
        "Apple Inc.",
        23,
        2024,
    )
    assert source["excerpt"] == "iPhone net sales were $201,183 million."


def test_finished_turn_is_saved_in_order_and_reloads(client, admin):
    thread = new_thread(client)
    parsed = events(ask(client, thread))
    streamed_id = parsed[0]["messageId"]

    history = client.get(f"/threads/{thread}/messages", headers=AUTH_ALICE).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["parts"][0]["text"] == "What was Apple's revenue?"
    assert history[1]["id"] == streamed_id
    assert history[1]["parts"][0]["text"] == ANSWER


def test_title_comes_from_first_question_only(client):
    thread = new_thread(client)
    ask(client, thread, "First   question\nabout Apple")
    ask(client, thread, "A second question")
    title = client.get("/threads", headers=AUTH_ALICE).json()[0]["title"]
    assert title == "First question about Apple"


def test_save_failure_sends_error_not_finish(client, admin):
    thread = new_thread(client)
    admin.fail_inserts_into = "chat_messages"
    types = [
        e if isinstance(e, str) else e["type"] for e in events(ask(client, thread))
    ]
    assert "error" in types and "finish" not in types
    admin.fail_inserts_into = None
    assert client.get(f"/threads/{thread}/messages", headers=AUTH_ALICE).json() == []


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"id": "a", "role": "assistant", "parts": [{"type": "text", "text": "hi"}]}],
        [{"id": "a", "role": "user", "parts": [{"type": "text", "text": "   "}]}],
    ],
)
def test_bad_message_lists_are_rejected_and_nothing_is_saved(client, admin, messages):
    thread = new_thread(client)
    body = {"threadId": thread, "messages": messages}
    assert client.post("/chat/stream", json=body, headers=AUTH_ALICE).status_code == 422
    assert admin.tables.get("chat_messages", []) == []
