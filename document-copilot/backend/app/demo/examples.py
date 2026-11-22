"""The demo: a few recorded questions anyone can open, and the notice shown for everything else.

Accounts that are not on FULL_ACCESS_EMAILS can only use these. The answers are real ones from
the assistant, recorded by evals/record_demo.py, so showing them costs no model call.
"""

from dataclasses import dataclass
from typing import Any

from app.demo.recorded import RECORDED

CONTACT_NAME = "Shrutika Modi"
CONTACT_URL = "https://www.linkedin.com/in/shrutika-modi-159b3ab4"

NOTICE_TITLE = "Live questions are available on request"
NOTICE_MESSAGE = (
    "In this preview you can explore Document Copilot through the sample questions on the "
    "home screen. To ask your own questions, see a live demo, or learn more about the "
    f"project, please contact {CONTACT_NAME}."
)


def notice_text() -> str:
    """The notice as one plain line, for places that cannot show a link button."""
    return f"{NOTICE_MESSAGE} {CONTACT_URL}"


@dataclass(frozen=True)
class DemoExample:
    id: str
    company: str
    kind: str  # what sort of question this is, shown on its card
    question: str
    steps: list[str]  # the progress lines the real assistant showed
    answer: str  # with [n] markers
    sources: list[dict[str, Any]]  # same shape chat/sources.py builds


EXAMPLES = [DemoExample(**recorded) for recorded in RECORDED]


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def find_example(text: str) -> DemoExample | None:
    """The example this question is, ignoring letter case and extra spaces, or None."""
    wanted = _normalize(text)
    return next((e for e in EXAMPLES if _normalize(e.question) == wanted), None)
