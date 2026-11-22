import pytest

from app.demo.checks import check_example, renumber


def source(label: int, excerpt: str, page: int = 10) -> dict:
    return {"label": label, "excerpt": excerpt, "page": page}


GOOD_ANSWER = (
    "AWS had operating income of $45,606 million on net sales of $128,725 million, "
    "a margin of 35.43% [1]."
)
GOOD = (
    GOOD_ANSWER,
    [source(1, "AWS | net sales 128,725 | operating income 45,606")],
)


def test_a_correct_answer_has_no_problems():
    assert check_example(*GOOD) == []


def test_a_wrong_percentage_is_caught():
    answer = GOOD[0].replace("35.43%", "35.45%")
    problems = check_example(answer, GOOD[1])
    assert len(problems) == 1 and "35.45%" in problems[0]


def test_a_percentage_quoted_in_a_source_is_fine():
    answer = "One customer was 12% of revenue [1]."
    assert (
        check_example(answer, [source(1, "one customer accounted for 12% of revenue")])
        == []
    )


def test_a_source_that_does_not_state_the_figure_is_caught():
    answer = "Net sales were $391,035 million [1][2]."
    sources = [
        source(1, "total net sales 391,035"),
        source(2, "revenue recognition policy"),
    ]
    problems = check_example(answer, sources)
    assert len(problems) == 1 and problems[0].startswith("[2]")


def test_a_narrative_answer_with_no_figures_skips_the_figure_rule():
    assert (
        check_example("Demand rose on new products [1].", [source(1, "any text")]) == []
    )


@pytest.mark.parametrize(
    "answer",
    ["Demand rose [1][3].", "Demand rose [2]."],
)
def test_gaps_and_wrong_order_are_caught(answer):
    sources = [source(n, "text") for n in (1, 2, 3)]
    assert any(
        "order of first use" in p or "do not match" in p
        for p in check_example(answer, sources)
    )


def test_renumber_makes_labels_follow_first_use_and_drops_unused_sources():
    answer = "A [1][3]. B [2][5]. C [1][3][6]."
    sources = [source(n, f"text {n}") for n in (1, 2, 3, 5, 6)]
    text, renumbered = renumber(answer, sources)
    assert text == "A [1][2]. B [3][4]. C [1][2][5]."
    assert [s["label"] for s in renumbered] == [1, 2, 3, 4, 5]
    assert [s["excerpt"] for s in renumbered] == [f"text {n}" for n in (1, 3, 2, 5, 6)]
    assert check_example(text, renumbered) == []


def test_renumber_refuses_a_marker_with_no_source():
    with pytest.raises(ValueError, match="no source"):
        renumber("A [4].", [source(1, "x")])


def test_a_marker_far_from_its_figure_is_caught():
    answer = (
        "AWS earned $45,606 million, North America earned $29,619 million, and "
        "International earned $4,750 million across the year, which together shows "
        "how the segments compare [1]."
    )
    sources = [source(1, "45,606 29,619 4,750")]
    problems = check_example(answer, sources)
    assert any("no marker right after $45,606" in p for p in problems)


def test_markers_right_after_each_figure_are_fine():
    answer = "AWS earned $45,606 million [1] and North America $29,619 million [1]."
    assert check_example(answer, [source(1, "45,606 29,619")]) == []


def test_an_answer_with_no_figures_needs_a_marker_in_every_sentence():
    answer = "Demand grew on new products [1]. Supply stayed tight in several regions."
    problems = check_example(answer, [source(1, "text")])
    assert len(problems) == 1 and problems[0].startswith("sentence has no marker")
    fixed = (
        "Demand grew on new products [1]. Supply stayed tight in several regions [1]."
    )
    assert check_example(fixed, [source(1, "text")]) == []


def test_a_percentage_split_across_table_cells_counts_as_quoted():
    answer = "One direct customer was 12% of total revenue [1]."
    assert (
        check_example(answer, [source(1, "| Direct Customer A | 12 | % | * |")]) == []
    )
