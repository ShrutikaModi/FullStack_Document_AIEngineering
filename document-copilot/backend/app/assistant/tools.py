import structlog
from pydantic_ai import ModelRetry, RunContext

from app.assistant.deps import DocumentAgentDeps
from app.retrieval.types import Passage, SearchFilters

log = structlog.get_logger()

MAX_WINDOW = 3  # how many neighbouring chunks either side the model may ask for
TOP_K = 8


def format_passage(passage_id: str, p: Passage) -> str:
    """One passage as the model sees it: a header it can cite from, then the text."""
    page = f"page {p.page}" if p.page else "page unknown"
    section = f", {p.section}" if p.section else ""
    return (
        f"[{passage_id}] {p.company} {p.form_type}, fiscal year {p.fiscal_year}, "
        f"filed {p.filing_date}, {page}{section}\n{p.content}"
    )


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    reason: str,
    query: str,
    tickers: list[str] | None = None,
    fiscal_years: list[int] | None = None,
    section: str | None = None,
) -> str:
    """Search the SEC 10-K filings and return the best matching passages, each with an id.

    Use this before answering anything. Search once per company or year when comparing, so
    each search stays focused. Cite only the ids this tool returns.

    Args:
        reason: One short sentence on why you are making this search (what you hope to
            find or check). Only used for debugging; it does not change the search.
        query: What to look for, in plain words (e.g. "iPhone net sales by category").
        tickers: Limit to these companies, e.g. ["AAPL"]. Omit to search all companies.
        fiscal_years: Limit to these fiscal years, e.g. [2023, 2024].
        section: Limit to a filing section by its start, e.g. "Item 1A" for risk factors
            or "Item 7" for management's discussion.
    """
    deps = ctx.deps
    log.info(
        "tool_call",
        tool="search_filings",
        reason=reason,
        query=query,
        tickers=tickers,
        fiscal_years=fiscal_years,
        section=section,
    )
    if deps.searches_left <= 0:
        return "Search limit reached. Answer using only the passages you already have."
    deps.searches_left -= 1

    filters = SearchFilters(
        tickers=[t.upper() for t in tickers or []],
        fiscal_years=list(fiscal_years or []),
        section_prefix=section,
    )
    passages = await deps.retriever.search(query, filters, top_k=TOP_K, neighbors=0)
    if not passages:
        return "No passages found. Try different words or fewer filters."
    return "\n\n".join(format_passage(deps.evidence.add(p), p) for p in passages)


async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps], reason: str, passage_id: str, window: int = 1
) -> str:
    """Show the text just before and after a passage you already found, for more context.

    Use this when a passage seems cut off (a table or sentence that continues). Reads are
    limited per question and a passage can be read only once at the same width, so read only
    what you need; everything you read stays available in your earlier results.

    Args:
        reason: One short sentence on why you need more context here. Only used for
            debugging; it does not change the result.
        passage_id: An id returned by search_filings, e.g. "P3".
        window: How many neighbouring chunks on each side (1 to 3).
    """
    deps = ctx.deps
    log.info(
        "tool_call",
        tool="read_surrounding_chunks",
        reason=reason,
        passage_id=passage_id,
        window=window,
    )
    passage = deps.evidence.get(passage_id)
    if passage is None:
        known = ", ".join(sorted(deps.evidence.ids())) or "none yet"
        raise ModelRetry(
            f"Unknown passage id {passage_id}. Passages you have: {known}."
        )

    window = max(1, min(window, MAX_WINDOW))
    already = deps.read_windows.get(passage_id, 0)
    if window <= already:
        # Refused without cost: the text is already in the model's earlier results.
        return (
            f"You already read the surrounding text of {passage_id} (up to {already} "
            "chunk(s) each side). It is in your earlier results; use it from there."
        )
    if deps.reads_left <= 0:
        return "Read limit reached. Answer using only the passages you already have."
    deps.reads_left -= 1
    deps.read_windows[passage_id] = window

    neighbors = (await deps.retriever.attach_neighbors([passage], window))[0].neighbors
    if not neighbors:
        return f"{passage_id} has no neighbouring text."
    return "\n\n".join(format_passage(deps.evidence.add(n), n) for n in neighbors)
