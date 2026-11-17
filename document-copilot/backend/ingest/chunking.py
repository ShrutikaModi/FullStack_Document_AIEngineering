"""Split a filing's Markdown into retrieval-sized chunks with page and section.

Pure functions, no I/O, so they are easy to unit test.
"""

import html
import re
from dataclasses import dataclass

# Token counts are estimated (about 4 characters per token) to avoid a tokenizer
# dependency. Targets are far below the embedding model's 8191-token limit.
CHARS_PER_TOKEN = 4
TARGET_TOKENS = 700
MAX_TOKENS = 1000
OVERLAP_TOKENS = 80

# "[[PAGE 12]]" is written by page_markers.py; the other forms are what Docling keeps
# for filings that print the page number as plain text: a bare "12", or Apple's
# "Apple Inc. | 2025 Form 10-K | 12".
MARKER_LINE = re.compile(r"^\[\[PAGE (\d{1,3})\]\]$")
PAGE_LINE = re.compile(r"^(?:[^|]{0,60}\|\s*\d{4} Form 10-K\s*\|\s*)?(\d{1,3})$")
LINK = re.compile(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\([^)]*\)")
# "---" / ":---:" mark the header separator row. A lone "-" is a real value (zero) in
# financial tables, so it must not match.
SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
# A section line: "Item 1A. Risk Factors", "ITEM 7.MANAGEMENT'S...", a table row, or the
# start of a paragraph ("Item 1A. Risk Factors. The following ...").
ITEM_LINE = re.compile(r"^(?:#+\s*)?\|?\s*Item\s+(\d{1,2}[A-C]?)\b", re.IGNORECASE)
MAX_ITEM_LINE = 100

# The 10-K item names are fixed by the SEC, so every company gets the same section text
# (handy for filtering) even though each formats its headings differently.
ITEMS = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer "
    "Purchases of Equity Securities",
    "6": "[Reserved]",
    "7": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "9C": "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership of Certain Beneficial Owners and Management and Related "
    "Stockholder Matters",
    "13": "Certain Relationships and Related Transactions, and Director Independence",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
    "16": "Form 10-K Summary",
}


@dataclass
class Chunk:
    index: int
    content: str
    page: int | None
    section: str | None
    token_count: int


@dataclass
class Block:
    text: str
    page: int | None
    section: str | None


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def section_name(line: str) -> str | None:
    """'Item 1A. Risk Factors' for a line that starts a 10-K item, else None."""
    match = ITEM_LINE.match(line)
    # Body text that merely mentions an item ("see Item 7 of ...") is long; headings are short,
    # except JPMorgan's, which run on into the paragraph ("Item 1A. Risk Factors. The ...").
    if not match or (
        len(line) > MAX_ITEM_LINE and not re.match(r"^Item \d+[A-C]?\. [A-Z]", line)
    ):
        return None
    number = match.group(1).upper()
    return f"Item {number}. {ITEMS[number]}" if number in ITEMS else None


def clean_table_row(line: str) -> str | None:
    """Drop empty cells and collapse repeats left by merged cells; None if nothing is left."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    kept: list[str] = []
    for cell in cells:
        if SEPARATOR_CELL.match(cell):
            return None  # the |---|---| separator row
        if cell and (not kept or kept[-1] != cell):
            kept.append(cell)
    return "| " + " | ".join(kept) + " |" if kept else None


def find_page_markers(lines: list[str]) -> dict[int, int]:
    """Line number -> page number, where that page ends on that line.

    Explicit [[PAGE n]] lines win. Otherwise use the longest run of bare numbers counting
    up by one: filings don't always start at 1 (cover page, table-of-contents numbers),
    so the real page numbers are the longest consecutive run, not the first numbers seen.
    """
    explicit = {
        number: int(match.group(1))
        for number, line in enumerate(lines)
        if (match := MARKER_LINE.match(line.strip()))
    }
    if explicit:
        return explicit

    candidates = []
    for number, line in enumerate(lines):
        match = PAGE_LINE.match(line.strip())
        if match:
            candidates.append((number, int(match.group(1))))
    if not candidates:
        return {}

    best_len = [1] * len(candidates)
    previous = [-1] * len(candidates)
    for i, (_, page) in enumerate(candidates):
        for j in range(i):
            if candidates[j][1] + 1 == page and best_len[j] + 1 > best_len[i]:
                best_len[i], previous[i] = best_len[j] + 1, j

    end = max(range(len(candidates)), key=best_len.__getitem__)
    markers = {}
    while end != -1:
        line_number, page = candidates[end]
        markers[line_number] = page
        end = previous[end]
    return markers


def split_into_blocks(markdown: str) -> list[Block]:
    """Paragraphs and whole tables, each tagged with its page and section."""
    lines = markdown.split("\n")
    markers = find_page_markers(lines)
    last_page = max(markers.values(), default=0)

    raw: list[tuple[str, int, str | None]] = []  # text, ending line, section
    section: str | None = None
    paragraph: list[str] = []
    table: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal paragraph, table, section
        if paragraph:
            raw.append(("\n".join(paragraph), end_line, section))
        if table:
            rows = [r for r in (clean_table_row(t) for t in table) if r]
            if rows:
                # Some filings (Amazon) put the item heading in a one-row table.
                section = (
                    section_name(rows[0].strip("| ").replace(" | ", " ")) or section
                )
                raw.append(("\n".join(rows), end_line, section))
        paragraph, table = [], []

    for number, line in enumerate(lines):
        stripped = line.strip()
        if number in markers or not stripped:
            flush(number)
        elif stripped.startswith("|"):
            if paragraph:
                flush(number)
            table.append(stripped)
        else:
            if table:
                flush(number)
            found = section_name(stripped)
            if found:
                flush(number)
                section = found
            paragraph.append(stripped)
    flush(len(lines))

    marker_lines = sorted(markers)
    blocks = []
    for text, end_line, block_section in raw:
        # A page number sits at the bottom of its page, so text belongs to the next marker.
        following = next((m for m in marker_lines if m >= end_line), None)
        if following is not None:
            page = markers[following]
        else:
            page = (
                last_page + 1 if last_page else None
            )  # text after the final page number
        blocks.append(Block(text, page, block_section))
    return blocks


def split_oversized(text: str) -> list[str]:
    """Break one block that is too big, by lines first and by characters as a last resort."""
    limit = MAX_TOKENS * CHARS_PER_TOKEN
    pieces: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:limit])
            line = line[limit:]
        if current and len(current) + len(line) + 1 > limit:
            pieces.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return pieces


def chunk_markdown(markdown: str) -> list[Chunk]:
    """Pack blocks into chunks. A chunk never crosses a page or section boundary, so the
    page and section stored with it are exactly where its text came from."""
    # Docling leaves HTML entities and link targets in; neither helps retrieval.
    markdown = LINK.sub(r"\1", html.unescape(markdown))
    target = TARGET_TOKENS * CHARS_PER_TOKEN
    overlap = OVERLAP_TOKENS * CHARS_PER_TOKEN
    chunks: list[Chunk] = []
    current: list[str] = []
    size = 0
    first: Block | None = None
    tail = ""  # end of the previous chunk, repeated at the start of the next
    tail_place: tuple[int | None, str | None] = (None, None)

    def emit() -> None:
        nonlocal current, size, first, tail, tail_place
        if not current or first is None:
            return
        body = "\n\n".join(current)
        # Overlap helps when a thought runs across chunks; it would mislead if it came
        # from another page or section.
        carried = tail if tail_place == (first.page, first.section) else ""
        content = f"{carried}\n\n{body}" if carried else body
        chunks.append(
            Chunk(
                len(chunks),
                content,
                first.page,
                first.section,
                estimate_tokens(content),
            )
        )
        tail = body[-overlap:].partition(" ")[2]  # start on a whole word
        tail_place = (first.page, first.section)
        current, size, first = [], 0, None

    for block in split_into_blocks(markdown):
        for piece in (
            split_oversized(block.text) if len(block.text) > target else [block.text]
        ):
            if first is not None and (
                size + len(piece) > target
                or (block.page, block.section) != (first.page, first.section)
            ):
                emit()
            if first is None:
                first = Block(piece, block.page, block.section)
            current.append(piece)
            size += len(piece)
    emit()
    return chunks
