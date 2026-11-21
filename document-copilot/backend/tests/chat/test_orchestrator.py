"""run_turn with a scripted fake model: what is streamed, and what happens on failure."""

import json
from uuid import uuid4

import pytest
import structlog
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from structlog.contextvars import merge_contextvars
from structlog.testing import LogCapture

from app.assistant.agent import build_agent
from app.chat import orchestrator
from app.chat.orchestrator import describe_tool_call, run_turn
from tests.assistant.test_agent import FakeRetriever
from tests.fake_supabase import FakeAdmin

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def logs():
    """Captures the log lines (with the turn's ids merged in, as in production).

    Failure paths log tracebacks; the default console renderer prints each one with every
    local variable, which takes many seconds. Capturing avoids that.
    """
    capture = LogCapture()
    previous = structlog.get_config()
    structlog.configure(processors=[merge_contextvars, capture])
    yield capture.entries
    structlog.configure(**previous)


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


async def test_a_content_filter_block_says_so_and_does_not_name_the_filter(logs):
    body = {
        "code": "content_filter",
        "innererror": {
            "content_filter_result": {
                "jailbreak": {"detected": True, "filtered": True},
                "hate": {"filtered": False, "severity": "safe"},
            }
        },
    }

    def blocked(messages, info):
        raise ModelHTTPError(400, "test-model", body)

    parsed, admin = await turn(blocked)
    assert parsed[-2]["errorText"] == orchestrator.CONTENT_BLOCKED
    assert "jailbreak" not in parsed[-2]["errorText"].lower()
    assert [
        e["filters"] for e in logs if e["event"] == "blocked by content filter"
    ] == [["jailbreak"]]
    assert "text-delta" not in types(parsed)
    assert admin.tables.get("chat_messages", []) == []


async def test_other_bad_requests_are_not_mistaken_for_content_blocks():
    def rejected(messages, info):
        raise ModelHTTPError(400, "test-model", {"code": "invalid_request"})

    parsed, _ = await turn(rejected)
    assert parsed[-2]["errorText"] == orchestrator.MODEL_UNAVAILABLE


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


def finished(logs):
    return [e for e in logs if e["event"] == "turn_finished"]


async def test_every_line_of_a_turn_carries_the_same_ids(logs):
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P1"}])
    )
    await turn(fn)
    assert [
        e["event"] for e in logs if e["event"] in ("turn_started", "turn_finished")
    ] == [
        "turn_started",
        "turn_finished",
    ]
    ids = {(e["request_id"], e["thread_id"], e["user_id"]) for e in logs}
    assert len(ids) == 1
    _, thread_id, user_id = ids.pop()
    assert (thread_id, user_id) == (THREAD["id"], "u")


async def test_a_good_turn_logs_how_it_went(logs):
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P1"}])
    )
    await turn(fn)
    (done,) = finished(logs)
    assert (done["outcome"], done["searches"], done["sources"]) == ("answered", 1, 1)
    assert done["ms"] >= 0
    started = next(e for e in logs if e["event"] == "turn_started")
    assert started["question_chars"] == len("How were iPhone sales?")
    # one model call per step: the search, then the answer
    calls_logged = [e for e in logs if e["event"] == "model_response"]
    assert len(calls_logged) == 2
    assert all("input_tokens" in e and e["ms"] >= 0 for e in calls_logged)
    search = next(e for e in logs if e["event"] == "tool_call")
    assert search["results"] > 0 and search["ms"] >= 0


async def test_the_question_text_never_reaches_the_logs(logs):
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P1"}])
    )
    await turn(fn)
    assert "How were iPhone sales?" not in str(logs)


async def test_a_citation_mistake_is_logged_with_the_broken_rule(logs):
    calls = iter([SEARCH, None])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P99"}])
    )
    await turn(fn)
    retries = [e for e in logs if e["event"] == "citation_retry"]
    assert retries and "P99" in " ".join(retries[0]["problems"])
    assert finished(logs)[0]["outcome"] == "grounding_failed"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (ModelHTTPError(503, "test-model", "unavailable"), "model_unavailable"),
        (
            ModelHTTPError(
                400,
                "test-model",
                {
                    "code": "content_filter",
                    "innererror": {
                        "content_filter_result": {"jailbreak": {"filtered": True}}
                    },
                },
            ),
            "content_blocked",
        ),
    ],
)
async def test_each_failure_is_logged_with_its_outcome(logs, failure, expected):
    def fn(messages, info):
        raise failure

    await turn(fn)
    assert finished(logs)[0]["outcome"] == expected


async def test_a_failing_search_is_logged_as_search_failed(logs):
    class BrokenRetriever:
        async def search(self, *args, **kwargs):
            raise RuntimeError("database down")

    calls = iter([SEARCH])
    fn = lambda m, info: next(calls, None) or answer(info, [])
    await turn(fn, retriever=BrokenRetriever())
    assert finished(logs)[0]["outcome"] == "search_failed"


async def test_a_turn_leaves_no_ids_behind_for_the_next_one(logs):
    calls = iter([SEARCH])
    fn = lambda m, info: (
        next(calls, None) or answer(info, [{"label": 1, "passage_id": "P1"}])
    )
    await turn(fn)
    assert structlog.contextvars.get_contextvars() == {}


async def test_a_browser_that_goes_away_is_logged_and_cleaned_up(logs):
    agent = build_agent(
        FunctionModel(
            lambda m, info: answer(
                info, []
            )  # never reached: we stop right after "start"
        )
    )
    stream = run_turn(
        FakeAdmin(),
        THREAD,
        "How were iPhone sales?",
        agent=agent,
        retriever=FakeRetriever(),
        user_id="u",
        history=[],
    )
    await anext(stream)  # the "start" event
    await stream.aclose()  # the browser went away
    assert finished(logs)[0]["outcome"] == "client_disconnected"
    assert structlog.contextvars.get_contextvars() == {}


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
