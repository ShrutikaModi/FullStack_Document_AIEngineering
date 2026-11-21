"""run_turn with a scripted fake model: what is streamed, and what happens on failure."""

import json
from uuid import uuid4

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from structlog.testing import capture_logs

from app.assistant.agent import build_agent
from app.chat import orchestrator
from app.chat.orchestrator import describe_tool_call, run_turn
from tests.assistant.test_agent import FakeRetriever
from tests.fake_supabase import FakeAdmin

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def quiet_logs():
    """Failure paths log tracebacks; the default console renderer prints each one with
    every local variable, which takes many seconds. Capturing the logs avoids that."""
    with capture_logs():
        yield


THREAD = {"id": str(uuid4()), "title": None}
SEARCH = ModelResponse(
    parts=[ToolCallPart("search_filings", {"reason": "r", "query": "iPhone sales"})]
)


def answer(info: AgentInfo, citations, text="Sales were $201,183 million [1]."):
    args = {"answer": text, "citations": citations, "enough_evidence": True}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])


async def turn(
    model_fn, admin=None, history=None, retriever=None
) -> tuple[list, FakeAdmin]:
    admin = admin or FakeAdmin()
    agent = build_agent(FunctionModel(model_fn))
    out = [
        item
        async for item in run_turn(
            admin,
            THREAD,
            "How were iPhone sales?",
            agent=agent,
            retriever=retriever or FakeRetriever(),
            user_id="u",
            history=history or [],
        )
    ]
    parsed = [
        e if e == "data: [DONE]\n\n" else json.loads(e.removeprefix("data: "))
        for e in out
    ]
    return parsed, admin


def types(parsed):
    return [e["type"] for e in parsed if isinstance(e, dict)]


async def test_a_valid_answer_is_streamed_and_saved():
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P1"}])
    )
    parsed, admin = await turn(fn)
    assert types(parsed)[-3:] == ["text-end", "data-citations", "finish"]
    assert [m["role"] for m in admin.tables["chat_messages"]] == ["user", "assistant"]


async def test_a_bad_citation_that_is_never_fixed_streams_no_text_and_saves_nothing():
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P99"}])
    )
    parsed, admin = await turn(fn)
    kinds = types(parsed)
    assert "text-delta" not in kinds and "finish" not in kinds
    assert parsed[-2]["errorText"] == orchestrator.GROUNDING_FAILED
    assert admin.tables.get("chat_messages", []) == []


async def test_a_model_outage_gives_a_clear_error_and_saves_nothing():
    def down(messages, info):
        raise ModelHTTPError(503, "test-model", "unavailable")

    parsed, admin = await turn(down)
    assert parsed[-2]["errorText"] == orchestrator.MODEL_UNAVAILABLE
    assert admin.tables.get("chat_messages", []) == []


async def test_a_failing_search_gives_a_clear_error_and_saves_nothing():
    class BrokenRetriever:
        async def search(self, *args, **kwargs):
            raise RuntimeError("database down")

    calls = iter([SEARCH])
    fn = lambda m, info: next(calls, None) or answer(info, [])
    parsed, admin = await turn(fn, retriever=BrokenRetriever())
    assert parsed[-2]["errorText"] == orchestrator.SEARCH_FAILED
    assert admin.tables.get("chat_messages", []) == []


async def test_the_previous_messages_reach_the_model():
    seen = []

    def fn(messages, info):
        seen.append(messages)
        if len(seen) == 1:
            return SEARCH
        return answer(info, [{"label": 1, "passage_id": "P1"}])

    history = [ModelRequest(parts=[UserPromptPart("Earlier question about Apple")])]
    await turn(fn, history=history)
    first_call = " ".join(str(p.content) for m in seen[0] for p in m.parts)
    assert "Earlier question about Apple" in first_call


def test_progress_lines():
    line = describe_tool_call(
        "search_filings",
        {"query": "iPhone sales", "tickers": ["AAPL"], "fiscal_years": [2024]},
    )
    assert line == "Searching AAPL FY2024 filings: iPhone sales"
    assert (
        describe_tool_call("search_filings", {"query": "q"}) == "Searching filings: q"
    )
    assert (
        describe_tool_call("read_surrounding_chunks", {})
        == "Reading the text around a passage"
    )
    assert describe_tool_call("final_result", {}) is None
