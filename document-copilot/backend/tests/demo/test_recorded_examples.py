"""The real recorded examples: they must be complete, cited and consistent with their sources."""

import re

import pytest

from app.demo.checks import check_example
from app.demo.examples import EXAMPLES, find_example

SOURCE_FIELDS = {
    "label",
    "chunkId",
    "company",
    "ticker",
    "formType",
    "fiscalYear",
    "filingDate",
    "page",
    "section",
    "excerpt",
    "sourceUrl",
}
MARKER = re.compile(r"\[(\d+)\]")


def test_there_are_three_examples_for_three_different_companies():
    assert len(EXAMPLES) == 3
    assert len({e.company for e in EXAMPLES}) == 3
    assert len({e.kind for e in EXAMPLES}) == 3


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_every_marker_has_a_source_and_every_source_is_used(example):
    marked = {int(n) for n in MARKER.findall(example.answer)}
    labels = [s["label"] for s in example.sources]
    assert marked and marked == set(labels) and len(labels) == len(set(labels))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_every_source_has_the_fields_the_screen_needs(example):
    for source in example.sources:
        assert set(source) == SOURCE_FIELDS
        assert source["excerpt"].strip() and source["sourceUrl"].startswith("https://")


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_the_answer_passes_the_recording_checks(example):
    assert check_example(example.answer, example.sources) == []


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_the_question_finds_its_own_example(example):
    assert find_example(example.question) is example
