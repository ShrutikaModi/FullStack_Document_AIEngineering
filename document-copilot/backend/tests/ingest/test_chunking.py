from ingest.chunking import MAX_TOKENS, chunk_markdown, clean_table_row, section_name


def test_table_row_drops_empty_cells_and_merged_repeats() -> None:
    assert clean_table_row("| Revenue | 5 | 5 | 5 |    |") == "| Revenue | 5 |"


def test_table_separator_row_is_dropped() -> None:
    assert clean_table_row("| --- | :---: |") is None


def test_pages_come_from_numbers_counting_up_and_close_each_page() -> None:
    chunks = chunk_markdown("First page.\n\n1\n\nSecond page.\n\n2\n\nThird page.")
    assert [c.page for c in chunks] == [1, 2, 3]
    assert all("\n1\n" not in c.content for c in chunks)


def test_stray_numbers_are_not_page_markers() -> None:
    chunks = chunk_markdown("Intro.\n\n57\n\nBody text.\n\n1\n\nMore.\n\n2\n\nEnd.")
    assert chunks[0].page == 1


def test_apple_style_footer_is_a_page_marker() -> None:
    chunks = chunk_markdown("Text.\n\nApple Inc. | 2025 Form 10-K | 1\n\nNext.")
    assert chunks[0].page == 1
    assert "Form 10-K" not in chunks[0].content


def test_explicit_page_markers_are_used_and_removed() -> None:
    chunks = chunk_markdown("Cover text.\n\n[[PAGE 1]]\n\nBody.\n\n[[PAGE 2]]")
    assert chunks[0].page == 1
    assert "[[PAGE" not in chunks[0].content


def test_no_markers_means_no_page() -> None:
    assert chunk_markdown("Just text with no page numbers.")[0].page is None


def test_section_names_are_the_same_whatever_the_heading_style() -> None:
    assert section_name("ITEM 1A.RISK FACTORS") == "Item 1A. Risk Factors"
    assert section_name("Item 1A. Risk Factors") == "Item 1A. Risk Factors"
    assert section_name("# Item 7. Management's Discussion") == (
        "Item 7. Management's Discussion and Analysis of Financial Condition "
        "and Results of Operations"
    )


def test_jpmorgan_style_heading_inside_a_paragraph() -> None:
    line = (
        "Item 1A. Risk Factors. The following discussion sets forth the material risk "
        * 3
    )
    assert section_name(line) == "Item 1A. Risk Factors"


def test_a_sentence_that_mentions_an_item_is_not_a_heading() -> None:
    assert (
        section_name("Item 7 of this report describes our results in detail " * 4)
        is None
    )


def test_chunks_take_the_latest_item_as_their_section() -> None:
    markdown = "Item 1A. Risk Factors\n\nSome risk.\n\nItem 7. Results\n\nNumbers here."
    sections = [c.section for c in chunk_markdown(markdown)]
    assert sections[0] == "Item 1A. Risk Factors"
    assert sections[-1].startswith("Item 7. Management")


def test_item_heading_in_a_table_row_sets_the_section() -> None:
    markdown = (
        "| Item 1A. | Item 1A. | Item 1A. | Risk Factors | Risk Factors |\n\nA risk."
    )
    assert chunk_markdown(markdown)[0].section == "Item 1A. Risk Factors"


def test_long_text_splits_and_chunks_stay_under_the_limit() -> None:
    markdown = "\n\n".join(f"Paragraph {i}. " + "word " * 200 for i in range(40))
    chunks = chunk_markdown(markdown)
    assert len(chunks) > 3
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(c.token_count <= MAX_TOKENS * 1.3 for c in chunks)


def test_one_huge_line_is_hard_split() -> None:
    assert len(chunk_markdown("x" * 20000)) > 1


def test_entities_and_link_targets_are_cleaned() -> None:
    chunk = chunk_markdown("AT&amp;T see [Table of Contents](#abc123) now")[0]
    assert chunk.content == "AT&T see Table of Contents now"


def test_overlap_between_chunks_starts_on_a_whole_word() -> None:
    markdown = "\n\n".join(f"Sentence number {i} " + "alpha " * 300 for i in range(12))
    second = chunk_markdown(markdown)[1].content
    assert second.startswith(("alpha", "Sentence"))


def test_a_lone_dash_cell_is_a_value_not_a_separator() -> None:
    assert clean_table_row("| Commercial paper | 1,066 | - | 2 |") == (
        "| Commercial paper | 1,066 | - | 2 |"
    )


def test_a_chunk_never_crosses_a_page_boundary() -> None:
    markdown = "Page one text.\n\n1\n\nPage two text.\n\n2\n\nPage three text."
    chunks = chunk_markdown(markdown)
    assert [c.page for c in chunks] == [1, 2, 3]
    assert all("two" not in c.content for c in chunks if c.page == 1)


def test_a_chunk_never_crosses_a_section_boundary() -> None:
    markdown = (
        "Item 1A. Risk Factors\n\nRisk text.\n\nItem 2. Properties\n\nWe own offices."
    )
    sections = [c.section for c in chunk_markdown(markdown)]
    assert (
        sections[0] == "Item 1A. Risk Factors" and sections[-1] == "Item 2. Properties"
    )
    assert len(sections) >= 2


def test_nested_bracket_links_are_cleaned() -> None:
    assert chunk_markdown("| Item 6. | [[Reserved]](#abc) | 19 |")[0].content == (
        "| Item 6. | [Reserved] | 19 |"
    )
