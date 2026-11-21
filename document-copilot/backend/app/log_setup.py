"""Log setup: every line is a set of named fields, and the ids of the current turn ride along.

`configure_logging` runs once at startup. After that, any module can do
`log = structlog.get_logger()` and `log.info("search_finished", results=8)`. The turn's
request_id / thread_id / user_id are bound once (see chat/orchestrator.py) and appear on
every line without the caller repeating them.
"""

from typing import Literal

import structlog


def configure_logging(log_format: Literal["console", "json"]) -> None:
    shared = [
        structlog.contextvars.merge_contextvars,  # the turn's ids
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if log_format == "json":
        renderer = [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Plain tracebacks: the default one prints every local variable, which is slow and
        # can put secrets (keys, tokens) on screen.
        renderer = [
            structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.plain_traceback
            )
        ]
    structlog.configure(
        processors=[*shared, *renderer],
        # Not cached, so tests can reconfigure and loggers already created pick it up.
        cache_logger_on_first_use=False,
    )
