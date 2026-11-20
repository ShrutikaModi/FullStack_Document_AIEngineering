import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, check_grounding

KNOWN = {"P1", "P2", "P3"}


def answer(
    text="iPhone sales rose [1].", citations=None, enough=True
) -> GroundedAnswer:
    if citations is None:
        citations = [Citation(label=1, passage_id="P1")]
    return GroundedAnswer(answer=text, citations=citations, enough_evidence=enough)


def problems(grounded: GroundedAnswer, known=KNOWN) -> list[str]:
    with pytest.raises(GroundingError) as error:
        check_grounding(grounded, known)
    return error.value.problems


def test_a_correct_answer_passes_unchanged():
    good = answer(
        "Sales rose [1] and services grew [2].",
        [
            Citation(label=1, passage_id="P1"),
            Citation(label=2, passage_id="P3"),
        ],
    )
    assert check_grounding(good, KNOWN) == good


def test_unused_citations_are_dropped_and_the_rest_sorted():
    grounded = answer(
        "Second [2] then first [1].",
        [
            Citation(label=2, passage_id="P2"),
            Citation(label=3, passage_id="P3"),  # never mentioned in the text
            Citation(label=1, passage_id="P1"),
        ],
    )
    result = check_grounding(grounded, KNOWN)
    assert [c.label for c in result.citations] == [1, 2]


def test_citing_a_passage_that_was_not_retrieved_fails():
    found = problems(answer(citations=[Citation(label=1, passage_id="P99")]))
    assert any("P99" in p and "not retrieved" in p for p in found)


def test_the_error_lists_the_passages_the_model_may_cite():
    found = problems(answer(citations=[Citation(label=1, passage_id="P99")]))
    assert "P1, P2, P3" in found[0]


def test_a_marker_in_the_text_without_a_citation_fails():
    found = problems(answer("Sales rose [1] and fell [2]."))
    assert any("[2]" in p and "no citation 2" in p for p in found)


def test_duplicate_labels_fail():
    duplicated = answer(
        citations=[
            Citation(label=1, passage_id="P1"),
            Citation(label=1, passage_id="P2"),
        ]
    )
    assert any("more than once" in p for p in problems(duplicated))


def test_an_answer_with_evidence_but_no_citations_fails():
    found = problems(answer("Sales rose.", citations=[]))
    assert any("must cite" in p for p in found)


def test_citations_that_are_never_marked_in_the_text_fail():
    found = problems(answer("Sales rose.", [Citation(label=1, passage_id="P1")]))
    assert any("must cite" in p for p in found)


def test_an_empty_answer_fails():
    assert any("empty" in p for p in problems(answer("   ", citations=[])))


def test_not_enough_evidence_with_no_citations_passes():
    honest = answer("The passages do not cover 2019.", citations=[], enough=False)
    assert check_grounding(honest, KNOWN) == honest


def test_not_enough_evidence_but_still_citing_fails():
    found = problems(answer("Unclear [1].", enough=False))
    assert any("not enough evidence" in p for p in found)


def test_not_enough_evidence_with_a_marker_in_the_text_fails():
    found = problems(answer("Unclear [1].", citations=[], enough=False))
    assert any("not enough evidence" in p for p in found)


def test_every_problem_is_reported_together():
    bad = answer(
        "Rose [1] and fell [2].",
        [
            Citation(label=1, passage_id="P99"),
            Citation(label=1, passage_id="P1"),
        ],
    )
    found = problems(bad)
    assert len(found) == 3  # duplicate label, unknown passage, missing citation 2


def test_only_the_single_number_marker_format_counts():
    # "[1, 2]" is not a citation marker, so the citation is unused and the answer is uncited.
    found = problems(answer("Rose [1, 2].", [Citation(label=1, passage_id="P1")]))
    assert any("must cite" in p for p in found)
