"""The citation rules: the check that stops an unsupported answer from reaching the analyst.

This file contains no AI, no database and no network. It only inspects the answer the model
produced and decides: is every citation real? It is the "fail closed" part of the product.

A running example used in the comments below. The model searched and was shown two passages,
which our code labelled P1 and P2. It then returned:

    answer:          "iPhone sales rose [1] while Services grew [2]."
    citations:       [ {label: 1, passage_id: "P1"}, {label: 2, passage_id: "P2"} ]
    enough_evidence: True

The [1] and [2] in the text are "markers". Each marker must point (through `citations`) to one
of the passages that was actually shown to the model in this turn.
"""

import re
from collections.abc import Collection

from app.assistant.outputs import GroundedAnswer

# Finds markers such as [1] or [12] in the answer text. Only a single number inside square
# brackets counts: "[1, 2]" is deliberately NOT a marker, so the model must write [1][2].
MARKER = re.compile(r"\[(\d+)\]")


class GroundingError(Exception):
    """The answer broke a citation rule. `problems` are worded so the model can fix them.

    In a later step this list is sent back to the model as a correction message, so each
    sentence says what is wrong AND what to do about it.
    """

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def check_grounding(
    answer: GroundedAnswer, known_passage_ids: Collection[str]
) -> GroundedAnswer:
    """Return the answer with unused citations removed, or raise GroundingError.

    `known_passage_ids` are the passages retrieved in THIS turn (e.g. {"P1", "P2"}). Nothing
    else may be cited, which is what stops the model from inventing a source.
    Every problem is reported at once, so the model can fix them all in a single retry.
    """
    problems: list[str] = []

    # Shown to the model in the error message so it knows what it is allowed to cite.
    allowed = ", ".join(sorted(known_passage_ids)) or "none (search first)"

    # RULE 1: each label may be used once. Two citations both numbered [1] would make it
    # impossible to tell which source a [1] in the text refers to.
    labels = [c.label for c in answer.citations]
    for label in sorted({n for n in labels if labels.count(n) > 1}):
        problems.append(f"Citation label [{label}] is used more than once.")

    # RULE 2: every citation must point to a passage that really was retrieved this turn.
    # A made-up id such as "P99" is caught here. This is the core anti-hallucination check.
    for citation in answer.citations:
        if citation.passage_id not in known_passage_ids:
            problems.append(
                f"Citation [{citation.label}] points to {citation.passage_id}, which was "
                f"not retrieved. Cite only these passages: {allowed}."
            )

    # RULE 3: every [n] marker written in the text needs a matching citation. Otherwise the
    # analyst would see "[3]" with no source behind it.
    in_text = {int(n) for n in MARKER.findall(answer.answer)}
    for label in sorted(in_text - set(labels)):
        problems.append(
            f"The text contains [{label}] but there is no citation {label}."
        )

    # "used" = citations whose marker really appears in the text. Citations the text never
    # mentions are harmless, so they are not an error; they are simply dropped at the end.
    used = [c for c in answer.citations if c.label in in_text]

    if answer.enough_evidence:
        # RULE 4: an answer that claims to be backed by evidence must be non-empty and must
        # actually cite something. "Always cite" from the client brief.
        if not answer.answer.strip():
            problems.append("The answer is empty.")
        elif not used:
            problems.append(
                "An answer with evidence must cite passages using [n] markers in the text."
            )
    elif in_text or answer.citations:
        # RULE 5: the opposite case. If the model says "not enough evidence", it must not
        # also cite sources: that would contradict itself. It should explain what is missing.
        problems.append(
            "When there is not enough evidence, do not cite anything: explain what the "
            "passages do not cover instead."
        )

    # Fail closed: any broken rule means no answer is returned at all.
    if problems:
        raise GroundingError(problems)

    # All rules passed. Return the answer with only the used citations, in label order
    # ([1], [2], [3]...), ready to be shown to the analyst.
    return answer.model_copy(update={"citations": sorted(used, key=lambda c: c.label)})
