"""Put printed page numbers into a filing's HTML before it is converted to Markdown.

Some filings (JPMorgan, newer Alphabet) keep their page number in a styled footer
that Docling drops, so the Markdown loses all page information. Those filings still
mark every page end with <hr style="page-break-after:always">, so we replace each
break with a visible "[[PAGE n]]" line that survives conversion. Chunking later
reads these lines to cite the right page.
"""

import html as html_lib
import re
from collections import Counter

PAGE_BREAK = re.compile(r"<hr[^>]*page-break-after:\s*always[^>]*/?>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
MARKER = "[[PAGE {}]]"
# How much HTML before a break to search for the footer, and how many text lines of it.
FOOTER_HTML_CHARS = 8000
FOOTER_LINES = 4


def footer_number(page_html: str) -> int | None:
    """The page number printed at the bottom of one page, if there is one."""
    text = TAG.sub("\n", page_html[-FOOTER_HTML_CHARS:])
    lines = [
        html_lib.unescape(line).replace("\xa0", " ").strip()
        for line in text.split("\n")
    ]
    for line in reversed([line for line in lines if line][-FOOTER_LINES:]):
        if re.fullmatch(r"\d{1,3}\.?", line):
            return int(line.rstrip("."))
    return None


def add_page_markers(html: str) -> tuple[str, int]:
    """Replace each page break with a [[PAGE n]] line. Returns (new html, markers added).

    Footers are missing on some pages (e.g. JPMorgan's even pages), so rather than trust
    each footer, find the usual gap between break position and printed number and apply it
    to every page.
    """
    pages = PAGE_BREAK.split(html)
    breaks = len(pages) - 1
    offsets = Counter(
        number - index
        for index in range(breaks)
        if (number := footer_number(pages[index])) is not None
    )
    if not offsets:
        return html, 0
    offset = offsets.most_common(1)[0][0]

    parts = [pages[0]]
    added = 0
    for index in range(breaks):
        page = index + offset
        if page >= 1:
            parts.append(f"<p>{MARKER.format(page)}</p>")
            added += 1
        parts.append(pages[index + 1])
    return "".join(parts), added
