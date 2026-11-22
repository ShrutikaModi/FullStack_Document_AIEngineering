"""Stricter checks for the recorded demo answers.

The live validator (grounding/validator.py) only proves that each citation points at a passage
the model was shown. That is enough for a live answer an analyst can follow up on, but the demo
answers are shown to every visitor, so they must also be tidy and correct: each source really
states what it is cited for, and any percentage is either quoted from a source or is the right
arithmetic on figures the answer states.

No AI, no database: used by evals/record_demo.py (to reject a bad recording and try again) and
by the tests (to guard the committed data).
"""

import re
from typing import Any

MARKER = re.compile(r"\[(\d+)\]")
# Dollar amounts and numbers with thousands separators: the figures a filing states.
FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+\b")
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")


def renumber(
    answer: str, sources: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    """Label the sources 1..n in the order their first marker appears, dropping unused ones.

    Only the numbers change, never the wording: the model sometimes cites [1][3] before [2],
    or leaves a gap, which looks careless on screen.
    """
    order: list[int] = []
    for marker in MARKER.findall(answer):
        if int(marker) not in order:
            order.append(int(marker))
    new_label = {old: new for new, old in enumerate(order, start=1)}
    by_label = {s["label"]: s for s in sources}
    missing = [n for n in order if n not in by_label]
    if missing:
        raise ValueError(f"marker(s) {missing} have no source")
    text = MARKER.sub(lambda m: f"[{new_label[int(m.group(1))]}]", answer)
    return text, [by_label[old] | {"label": new_label[old]} for old in order]


def _digits(figure: str) -> str:
    return re.sub(r"[^\d.]", "", figure)


# How far after a figure its marker may come (characters), within the same sentence.
MAX_MARKER_DISTANCE = 80
SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def _misplaced_markers(answer: str) -> list[str]:
    """Markers belong right after what they support, not collected at the end.

    A figure must be followed by a marker soon, within its own sentence. An answer that
    states no figures must carry a marker in every full sentence.
    """
    problems: list[str] = []
    flat = answer.replace("\n", " ")
    figures = list(FIGURE.finditer(flat))
    for figure in figures:
        rest = flat[figure.end() :]
        marker = MARKER.search(rest)
        end = SENTENCE_END.search(rest)
        if (
            marker is None
            or marker.start() > MAX_MARKER_DISTANCE
            or (end is not None and end.start() < marker.start())
        ):
            problems.append(f"no marker right after {figure.group(0).strip()}")
    if not figures:
        for sentence in re.split(r"(?<=[.!?])\s+", flat):
            if len(sentence.split()) >= 5 and not MARKER.search(sentence):
                problems.append(f"sentence has no marker: {sentence[:50]}...")
    return problems


def check_example(answer: str, sources: list[dict[str, Any]]) -> list[str]:
    """Everything wrong with a recorded answer, in plain words. Empty means it is fine."""
    problems: list[str] = []

    markers = [int(n) for n in MARKER.findall(answer)]
    labels = [s["label"] for s in sources]
    first_use = list(dict.fromkeys(markers))
    if not markers:
        problems.append("the answer has no citation markers")
    if set(markers) != set(labels):
        problems.append(f"markers {sorted(set(markers))} do not match sources {labels}")
    if first_use != list(range(1, len(first_use) + 1)):
        problems.append(f"labels are not 1..n in order of first use: {first_use}")

    problems += _misplaced_markers(answer)

    # Commas dropped so "391,035" and "391035" match; table cells like "12 | %" read as "12%".
    excerpts = [
        re.sub(r"\s*\|\s*%", "%", s["excerpt"].replace(",", "")) for s in sources
    ]
    figures = {_digits(f) for f in FIGURE.findall(answer)}

    # A source cited for a figure must contain at least one of the figures the answer states.
    # (Narrative answers state no figures, so this rule does not apply to them.)
    if figures:
        for source, excerpt in zip(sources, excerpts, strict=True):
            if not any(f in excerpt for f in figures):
                problems.append(
                    f"[{source['label']}] (page {source['page']}) contains none of the "
                    "figures the answer states"
                )

    # A percentage must be quoted from a source or be the right ratio of two stated figures.
    numbers = [float(f) for f in figures]
    for text in PERCENT.findall(answer):
        quoted = any(
            re.search(rf"(?<![\d.]){re.escape(text)}\s?%", e) for e in excerpts
        )
        decimals = len(text.split(".")[1]) if "." in text else 0
        tolerance = 0.5 * 10**-decimals + 1e-9
        computed = any(
            abs(100 * a / b - float(text)) <= tolerance
            for a in numbers
            for b in numbers
            if a != b and b
        )
        if not quoted and not (decimals and computed):
            problems.append(
                f"{text}% is neither quoted from a source nor the right ratio of two "
                "figures in the answer"
            )
    return problems
