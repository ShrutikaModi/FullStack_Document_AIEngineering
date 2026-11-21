"""One chat turn, end to end: the agent searches, the answer is checked, then it is streamed.

The order matters. The model works silently while the browser shows progress lines; only
after its answer has passed the citation rules (inside the agent) do we stream any text.
So an analyst never sees an unchecked answer. If anything fails, they see a plain error and
nothing is saved.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ToolCallPart
from supabase import AsyncClient

from app.assistant.deps import DocumentAgentDeps
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
SEARCH_FAILED = "Something went wrong while searching the filings. Please try again."
SAVE_FAILED = "Could not save this conversation."


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
    async with agent.iter(user_text, deps=deps, message_history=history) as run:
        async for node in run:
            if Agent.is_call_tools_node(node):
                for part in node.model_response.parts:
                    if isinstance(part, ToolCallPart):
                        line = describe_tool_call(part.tool_name, part.args_as_dict())
                        if line:
                            yield status_event(line)
    yield run.result.output


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

    Nothing is saved if the turn fails or the client disconnects mid-stream.
    """
    asked_at = datetime.now(UTC)
    message_id, text_id = str(uuid4()), str(uuid4())
    deps = DocumentAgentDeps(
        user_id=user_id, thread_id=str(thread["id"]), retriever=retriever
    )

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
        log.warning("grounding failed", thread_id=thread["id"], exc_info=True)
        yield event({"type": "error", "errorText": GROUNDING_FAILED})
        yield DONE
        return
    except ModelAPIError:
        log.exception("model call failed", thread_id=thread["id"])
        yield event({"type": "error", "errorText": MODEL_UNAVAILABLE})
        yield DONE
        return
    except Exception:
        # Tools run inside the agent, so a database or embedding failure lands here.
        log.exception("agent run failed", thread_id=thread["id"])
        yield event({"type": "error", "errorText": SEARCH_FAILED})
        yield DONE
        return

    if answer is None:  # cannot happen; fail closed rather than stream nothing
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
        "parts": [{"type": "text", "text": text}],
        "created_at": datetime.now(UTC).isoformat(),
    }
    try:
        await save_turn(
            admin, thread, user_message, assistant_message, thread_title(user_text)
        )
    except Exception:
        log.exception("could not save chat turn", thread_id=thread["id"])
        yield event({"type": "error", "errorText": SAVE_FAILED})
    else:
        yield event({"type": "finish"})
    yield DONE
