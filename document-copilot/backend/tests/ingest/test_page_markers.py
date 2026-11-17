from ingest.page_markers import add_page_markers, footer_number

BREAK = '<hr style="page-break-after:always"/>'


def page(text: str, number: str = "") -> str:
    footer = f"<div><span>{number}</span></div>" if number else ""
    return f"<p>{text}</p>{footer}"


def test_footer_number_reads_the_last_number_on_the_page() -> None:
    assert footer_number(page("Body", "12")) == 12
    assert footer_number(page("Body", "2. ")) == 2


def test_footer_number_is_none_without_a_number() -> None:
    assert footer_number(page("Only words here")) is None


def test_markers_replace_page_breaks_with_printed_numbers() -> None:
    html = BREAK.join([page("cover"), page("A", "1"), page("B", "2"), page("C")])
    result, added = add_page_markers(html)
    assert added == 2  # the cover page (before page 1) gets no marker
    assert "[[PAGE 1]]" in result and "[[PAGE 2]]" in result
    assert "page-break" not in result
    assert result.index("A") < result.index("[[PAGE 1]]") < result.index("B")


def test_pages_without_a_footer_get_the_usual_offset() -> None:
    html = BREAK.join(
        [
            page("cover"),
            page("A", "1"),
            page("B", "2"),
            page("C"),
            page("D", "4"),
            page("E"),
        ]
    )
    result, _ = add_page_markers(html)
    assert "[[PAGE 3]]" in result


def test_no_footers_means_no_markers() -> None:
    html = BREAK.join([page("a"), page("b"), page("c")])
    assert add_page_markers(html) == (html, 0)
