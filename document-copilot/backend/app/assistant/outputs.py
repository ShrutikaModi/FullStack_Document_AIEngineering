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

    # The Field descriptions below are sent to the model with the answer format, so each one
    # is an instruction to the model written next to the field it is filling in.
    answer: str = Field(
        description=(
            "The reply to the analyst. Put a marker like [1] right after every factual "
            "claim. Write [1][2], never [1, 2]. Every marker needs a matching entry in "
            "`citations`."
        )
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description=(
            "One entry per marker used in `answer`: `label` is the marker number and "
            "`passage_id` is the id (like P3) of the retrieved passage that supports the "
            "claim. Leave empty when enough_evidence is false."
        ),
    )
    # False when the passages don't answer the question. The answer then explains what is
    # missing, and must not contain citations.
    enough_evidence: bool = Field(
        description=(
            "True if the retrieved passages support an answer, even a partial one (then "
            "say what is missing). False only when they do not answer the question at "
            "all; then cite nothing and explain what was searched and what is missing."
        )
    )
