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


def stream_response(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events, media_type="text/event-stream", headers=STREAM_HEADERS
    )
