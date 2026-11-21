"""One chat turn, end to end: the agent searches, the answer is checked, then it is streamed.

The order matters. The model works silently while the browser shows progress lines; only
after its answer has passed the citation rules (inside the agent) do we stream any text.
So an analyst never sees an unchecked answer. If anything fails, they see a plain error and
nothing is saved.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

import structlog
from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
)
from pydantic_ai.messages import ModelMessage, ToolCallPart
from supabase import AsyncClient

from app.assistant.deps import MAX_SEARCHES, DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.chat.messages import thread_title
from app.chat.sources import build_sources
from app.chat.streaming import DONE, citations_event, event, status_event, text_pieces
from app.database.chats import Row, save_turn
from app.retrieval.retriever import DocumentRetriever

log = structlog.get_logger()

# What the analyst is told when a turn fails. Details go to the log, not to the screen.
GROUNDING_FAILED = (
    "I could not produce a fully sourced answer. Please try rephrasing the question."
)
MODEL_UNAVAILABLE = "The assistant is unavailable right now. Please try again."
# Which Azure filter fired is logged, not shown: naming it would help someone probing the
# system word around it, and filters can occasionally block an ordinary question.
CONTENT_BLOCKED = (
    "This question was blocked by the content filter. "
    "Please rephrase it and ask about the filings."
)
SEARCH_FAILED = "Something went wrong while searching the filings. Please try again."
SAVE_FAILED = "Could not save this conversation."


def blocked_categories(error: ModelAPIError) -> list[str] | None:
    """The Azure filters that blocked the request, or None if this is not a content block.

    Azure answers a blocked prompt with HTTP 400 and code "content_filter"; the body says
    which detectors fired (for example "jailbreak").
    """
    if not isinstance(error, ModelHTTPError) or error.status_code != 400:
        return None
    body = error.body
    if not isinstance(body, dict) or body.get("code") != "content_filter":
        return None
    results = (body.get("innererror") or {}).get("content_filter_result") or {}
    return [name for name, hit in results.items() if hit.get("filtered")]


def describe_tool_call(name: str, args: dict[str, Any]) -> str | None:
    """The progress line for a tool call, or None for calls that are not worth showing."""
    if name == "search_filings":
        years = [f"FY{y}" for y in args.get("fiscal_years") or []]
        scope = " ".join([*(args.get("tickers") or []), *years])
        return (
            f"Searching {scope + ' ' if scope else ''}filings: {args.get('query', '')}"
        )
    if name == "read_surrounding_chunks":
        return "Reading the text around a passage"
    return None  # e.g. the final answer being delivered


async def run_agent(
    agent: Agent[DocumentAgentDeps, GroundedAnswer],
    user_text: str,
    deps: DocumentAgentDeps,
    history: list[ModelMessage],
) -> AsyncIterator[str | GroundedAnswer]:
    """Run the agent; yield a progress line whenever it uses a tool, then the final answer.

    `agent.iter` hands us each step as it happens, which is how we can show progress
    without the tools knowing anything about the browser.
    """
    mark = perf_counter()
    async with agent.iter(user_text, deps=deps, message_history=history) as run:
        async for node in run:
            took, mark = perf_counter() - mark, perf_counter()
            if Agent.is_call_tools_node(node):
                # The model call finished just before this node arrived, so `took` is
                # how long the model needed for this step.
                usage = node.model_response.usage
                log.info(
                    "model_response",
                    ms=round(took * 1000),
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                )
                for part in node.model_response.parts:
                    if isinstance(part, ToolCallPart):
                        line = describe_tool_call(part.tool_name, part.args_as_dict())
                        if line:
                            yield status_event(line)
    yield run.result.output


@dataclass
class TurnOutcome:
    """How the turn ended, for the `turn_finished` log line.

    Stays "client_disconnected" unless the turn sets something else: if the browser goes
    away mid-stream the generator is closed before it reaches any of the assignments.
    """

    name: str = "client_disconnected"
    sources: int = 0


async def run_turn(
    admin: AsyncClient,
    thread: Row,
    user_text: str,
    *,
    agent: Agent[DocumentAgentDeps, GroundedAnswer],
    retriever: DocumentRetriever,
    user_id: str,
    history: list[ModelMessage],
) -> AsyncIterator[str]:
    """One chat turn: agent -> verified answer -> stream -> save both messages.

    Nothing is saved if the turn fails or the client disconnects mid-stream. Every log line
    written during the turn carries its ids; a `turn_finished` line says how it ended.
    """
    started = perf_counter()
    # The assistant message id doubles as the request id, so a log line can be matched to
    # the saved message (and to the `messageId` the browser received).
    message_id = str(uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=message_id, thread_id=str(thread["id"]), user_id=user_id
    )
    deps = DocumentAgentDeps(
        user_id=user_id, thread_id=str(thread["id"]), retriever=retriever
    )
    outcome = TurnOutcome()
    # Lengths only: the question is the analyst's own words and stays out of the logs.
    log.info("turn_started", question_chars=len(user_text), history=len(history))
    try:
        async for chunk in stream_turn(
            admin, thread, user_text, message_id, agent, deps, history, outcome
        ):
            yield chunk
    finally:
        log.info(
            "turn_finished",
            outcome=outcome.name,
            ms=round((perf_counter() - started) * 1000),
            searches=MAX_SEARCHES - deps.searches_left,
            sources=outcome.sources,
        )
        structlog.contextvars.clear_contextvars()


async def stream_turn(
    admin: AsyncClient,
    thread: Row,
    user_text: str,
    message_id: str,
    agent: Agent[DocumentAgentDeps, GroundedAnswer],
    deps: DocumentAgentDeps,
    history: list[ModelMessage],
    outcome: TurnOutcome,
) -> AsyncIterator[str]:
    asked_at = datetime.now(UTC)
    text_id = str(uuid4())

    yield event({"type": "start", "messageId": message_id})

    answer: GroundedAnswer | None = None
    try:
        async for item in run_agent(agent, user_text, deps, history):
            if isinstance(item, GroundedAnswer):
                answer = item
            else:
                yield item
    except UnexpectedModelBehavior:
        # The model kept breaking the citation rules (or sent unusable output).
        outcome.name = "grounding_failed"
        log.warning("grounding failed", exc_info=True)
        yield event({"type": "error", "errorText": GROUNDING_FAILED})
        yield DONE
        return
    except ModelAPIError as error:
        blocked = blocked_categories(error)
        if blocked is not None:
            outcome.name = "content_blocked"
            log.warning("blocked by content filter", filters=blocked)
            yield event({"type": "error", "errorText": CONTENT_BLOCKED})
            yield DONE
            return
        outcome.name = "model_unavailable"
        log.exception("model call failed")
        yield event({"type": "error", "errorText": MODEL_UNAVAILABLE})
        yield DONE
        return
    except Exception:
        # Tools run inside the agent, so a database or embedding failure lands here.
        outcome.name = "search_failed"
        log.exception("agent run failed")
        yield event({"type": "error", "errorText": SEARCH_FAILED})
        yield DONE
        return

    if answer is None:  # cannot happen; fail closed rather than stream nothing
        outcome.name = "grounding_failed"
        yield event({"type": "error", "errorText": GROUNDING_FAILED})
        yield DONE
        return

    text = answer.answer.strip()
    sources = build_sources(answer, deps.evidence)

    # Only now, with a verified answer in hand, does any answer text reach the browser.
    yield event({"type": "text-start", "id": text_id})
    for piece in text_pieces(text):
        yield event({"type": "text-delta", "id": text_id, "delta": piece})
    yield event({"type": "text-end", "id": text_id})
    if sources:
        yield citations_event(sources)

    source_parts = (
        [{"type": "data-citations", "data": {"sources": sources}}] if sources else []
    )
    user_message = {
        "id": str(uuid4()),
        "thread_id": thread["id"],
        "role": "user",
        "content": user_text,
        "parts": [{"type": "text", "text": user_text}],
        "created_at": asked_at.isoformat(),
    }
    assistant_message = {
        "id": message_id,
        "thread_id": thread["id"],
        "role": "assistant",
        "content": text,
        # The sources are stored with the message, so a reloaded thread shows them again.
        "parts": [{"type": "text", "text": text}, *source_parts],
        "created_at": datetime.now(UTC).isoformat(),
    }
    citation_rows = [
        {"message_id": message_id, "chunk_id": s["chunkId"], "label": s["label"]}
        for s in sources
    ]
    try:
        await save_turn(
            admin,
            thread,
            user_message,
            assistant_message,
            thread_title(user_text),
            citation_rows,
        )
    except Exception:
        outcome.name = "save_failed"
        log.exception("could not save chat turn")
        yield event({"type": "error", "errorText": SAVE_FAILED})
    else:
        outcome.name = "answered"
        outcome.sources = len(sources)
        yield event({"type": "finish"})
    yield DONE
