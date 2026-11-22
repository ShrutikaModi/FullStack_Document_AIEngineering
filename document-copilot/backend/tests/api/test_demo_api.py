"""Who gets the real assistant and who gets the demo, decided on the server."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.function import FunctionModel

from app.assistant.agent import build_agent
from app.config import settings
from app.demo.examples import CONTACT_URL
from app.main import app
from tests.assistant.test_agent import FakeRetriever
from tests.fake_demo import FAKE_EXAMPLE, QUESTION, use_fake_example
from tests.fake_supabase import FakeAdmin

OWNER = {"Authorization": "Bearer owner"}
GUEST = {"Authorization": "Bearer guest"}
UNCONFIRMED = {"Authorization": "Bearer unconfirmed"}
model_calls: list = []


def forbidden_model(messages, info):
    model_calls.append(messages)
    raise AssertionError("a demo account must never reach the model")


@pytest.fixture
def client(monkeypatch):
    use_fake_example(monkeypatch)
    model_calls.clear()
    monkeypatch.setattr(settings, "full_access_emails", ["owner@example.com"])
    fake = FakeAdmin()
    fake.add_user("owner", str(uuid4()), "Owner@Example.com")  # letter case differs
    fake.add_user("guest", str(uuid4()), "guest@example.com")
    # Has the owner's address but never confirmed it: must not get full access.
    fake.add_user("unconfirmed", str(uuid4()), "owner@example.com", confirmed=False)
    app.state.supabase_admin = fake
    app.state.retriever = FakeRetriever()
    app.state.agent = build_agent(FunctionModel(forbidden_model))
    return TestClient(app)


def stream(client, headers, text):
    thread_id = client.post("/threads", headers=headers).json()["id"]
    body = {
        "threadId": thread_id,
        "messages": [
            {"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}
        ],
    }
    response = client.post("/chat/stream", json=body, headers=headers)
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.split("\n\n")
        if line.startswith("data: {")
    ]


def test_the_demo_info_needs_a_login(client):
    assert client.get("/demo").status_code == 401


def test_a_guest_gets_the_sample_questions_and_the_notice(client):
    info = client.get("/demo", headers=GUEST).json()
    assert info["demo"] is True
    assert info["questions"] == [
        {
            "id": "fake-apple",
            "company": "Apple",
            "kind": "Single figure",
            "text": QUESTION,
        }
    ]
    assert info["notice"]["title"] and "Shrutika Modi" in info["notice"]["message"]
    assert info["notice"]["contact_url"] == CONTACT_URL
    assert CONTACT_URL.startswith("https://www.linkedin.com/in/")


def test_the_owner_is_not_in_demo_mode_even_with_different_letter_case(client):
    assert client.get("/demo", headers=OWNER).json() == {
        "demo": False,
        "questions": [],
        "notice": None,
    }


def test_an_unconfirmed_account_with_the_owners_address_is_still_demo(client):
    assert client.get("/demo", headers=UNCONFIRMED).json()["demo"] is True
    events = stream(client, UNCONFIRMED, "Why did margins improve?")
    assert events[-1]["type"] == "error"
    assert model_calls == []


def test_a_guest_can_run_an_example_without_the_model(client):
    events = stream(client, GUEST, QUESTION)
    assert [e["type"] for e in events][-1] == "finish"
    assert FAKE_EXAMPLE.answer in "".join(
        e["delta"] for e in events if e["type"] == "text-delta"
    )
    assert model_calls == []


def test_a_guest_typing_their_own_question_gets_the_notice_and_no_model_call(client):
    events = stream(client, GUEST, "What is NVIDIA's revenue?")
    assert events[-1]["type"] == "error"
    assert "Shrutika Modi" in events[-1]["errorText"]
    assert CONTACT_URL in events[-1]["errorText"]
    assert model_calls == []


def test_the_owner_still_reaches_the_real_assistant(client):
    # The model stand-in refuses to answer, which only proves the owner's question reached it.
    stream(client, OWNER, "What was Apple's revenue?")
    assert len(model_calls) == 1
