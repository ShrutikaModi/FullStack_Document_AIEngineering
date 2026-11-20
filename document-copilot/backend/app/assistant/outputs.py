from pydantic import BaseModel, Field


class Citation(BaseModel):
    """One source reference: "the [1] in my answer comes from passage P3"."""

    label: int = Field(ge=1)  # the [n] marker used in the answer text (1, 2, 3, ...)
    # "P3": the short id the model saw next to a passage in the search results.
    passage_id: str


class GroundedAnswer(BaseModel):
    """What the model must return: text with [n] markers, and what each marker points to.

    Example:
        answer="iPhone sales rose [1] while Services grew [2]."
        citations=[Citation(label=1, passage_id="P1"), Citation(label=2, passage_id="P2")]
        enough_evidence=True

    The model only supplies ids. The text shown to the analyst under each citation is later
    taken from our own database, never from the model, so it cannot be altered.
    """

    answer: str
    citations: list[Citation] = []
    # False when the passages don't answer the question. The answer then explains what is
    # missing, and must not contain citations.
    enough_evidence: bool
