"""Log setup: readable lines locally, one JSON object per line in production."""

import json

import pytest
import structlog

from app.log_setup import configure_logging


@pytest.fixture(autouse=True)
def restore_logging():
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def test_json_lines_have_the_event_fields_and_the_turn_ids(capsys):
    configure_logging("json")
    structlog.contextvars.bind_contextvars(
        request_id="r1", thread_id="t1", user_id="u1"
    )
    structlog.get_logger().info("search_done", results=8, ms=412)
    line = json.loads(capsys.readouterr().out)
    assert line["event"] == "search_done"
    assert (line["results"], line["ms"]) == (8, 412)
    assert (line["request_id"], line["thread_id"], line["user_id"]) == (
        "r1",
        "t1",
        "u1",
    )
    assert line["level"] == "info" and line["timestamp"].endswith("Z")


def test_json_errors_include_the_traceback_as_text(capsys):
    configure_logging("json")
    try:
        raise ValueError("boom")
    except ValueError:
        structlog.get_logger().exception("it failed")
    line = json.loads(capsys.readouterr().out)
    assert line["level"] == "error"
    assert "ValueError: boom" in line["exception"]


def test_console_lines_are_readable_and_show_the_ids(capsys):
    configure_logging("console")
    structlog.contextvars.bind_contextvars(request_id="r1")
    structlog.get_logger().info("search_done", results=8)
    out = capsys.readouterr().out
    assert "search_done" in out and "results" in out and "request_id" in out
