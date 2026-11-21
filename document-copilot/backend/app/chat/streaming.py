import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.responses import StreamingResponse

# Headers the AI SDK client expects on a UI message stream.
STREAM_HEADERS = {
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "x-vercel-ai-ui-message-stream": "v1",
    "x-accel-buffering": "no",
}

DONE = "data: [DONE]\n\n"


def event(payload: dict[str, Any]) -> str:
    """One server-sent event carrying a JSON chunk."""
    return f"data: {json.dumps(payload)}\n\n"


def status_event(text: str) -> str:
    """A progress line ("Searching Apple FY2024..."). Transient: shown, never stored."""
    return event({"type": "data-status", "data": {"text": text}, "transient": True})


def citations_event(sources: list[dict[str, Any]]) -> str:
    """The source cards for the answer just streamed."""
    return event({"type": "data-citations", "data": {"sources": sources}})


def text_pieces(text: str, size: int = 24) -> list[str]:
    """Cut the verified answer into small pieces so it appears progressively."""
    return [text[i : i + size] for i in range(0, len(text), size)]


def stream_response(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events, media_type="text/event-stream", headers=STREAM_HEADERS
    )
