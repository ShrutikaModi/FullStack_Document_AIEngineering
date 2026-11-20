from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic_ai import ModelRetry

from app.assistant.deps import DocumentAgentDeps
from app.assistant.tools import MAX_WINDOW, read_surrounding_chunks, search_filings
from app.retrieval.types import Passage

pytestmark = pytest.mark.anyio


def passage(
    n: int, page: int | None = None, section: str | None = "Item 7. MD&A"
) -> Passage:
    return Passage(
        chunk_id=UUID(int=n),
        document_id=UUID(int=999),
        chunk_index=n,
        ticker="AAPL",
        company="Apple Inc.",
        form_type="10-K",
        fiscal_year=2024,
        filing_date=date(2024, 11, 1),
        source_url="u",
        page=page,
        section=section,
        content=f"text {n}",
    )


class FakeRetriever:
    """Records how it was called and returns what the test gave it."""

    def __init__(self, results=(), neighbors=()):
        self.results, self.neighbor_passages = list(results), list(neighbors)
        self.searches: list[tuple] = []
        self.window_asked: list[int] = []

    async def search(self, query, filters, top_k, neighbors):
        self.searches.append((query, filters, top_k, neighbors))
        return self.results

    async def attach_neighbors(self, passages, window):
        self.window_asked.append(window)
        return [replace(p, neighbors=tuple(self.neighbor_passages)) for p in passages]


def make(retriever, **kwargs):
    deps = DocumentAgentDeps(user_id="u", thread_id="t", retriever=retriever, **kwargs)
    return deps, SimpleNamespace(deps=deps)


async def test_search_passes_the_query_and_cleaned_filters_to_the_retriever():
    retriever = FakeRetriever([passage(1)])
    _, ctx = make(retriever)
    await search_filings(
        ctx, "iPhone sales", tickers=["aapl"], fiscal_years=[2023], section="Item 7"
    )
    query, filters, top_k, neighbors = retriever.searches[0]
    assert query == "iPhone sales"
    assert (filters.tickers, filters.fiscal_years, filters.section_prefix) == (
        ["AAPL"],
        [2023],
        "Item 7",
    )
    assert (top_k, neighbors) == (8, 0)


async def test_results_are_registered_in_the_log_and_shown_with_their_ids():
    deps, ctx = make(FakeRetriever([passage(1, page=23), passage(2, page=24)]))
    shown = await search_filings(ctx, "q")
    assert deps.evidence.ids() == {"P1", "P2"}
    assert "[P1]" in shown and "[P2]" in shown


async def test_the_model_sees_company_year_date_page_section_and_text():
    _, ctx = make(FakeRetriever([passage(1, page=23)]))
    shown = await search_filings(ctx, "q")
    for part in (
        "Apple Inc.",
        "10-K",
        "fiscal year 2024",
        "filed 2024-11-01",
        "page 23",
        "Item 7. MD&A",
        "text 1",
    ):
        assert part in shown


async def test_a_missing_page_reads_page_unknown():
    _, ctx = make(FakeRetriever([passage(1, page=None)]))
    assert "page unknown" in await search_filings(ctx, "q")


async def test_no_results_gives_a_helpful_message():
    _, ctx = make(FakeRetriever([]))
    assert "No passages found" in await search_filings(ctx, "q")


async def test_searches_stop_at_the_limit_without_calling_the_retriever():
    retriever = FakeRetriever([passage(1)])
    _, ctx = make(retriever, searches_left=1)
    await search_filings(ctx, "first")
    refused = await search_filings(ctx, "second")
    assert "Search limit reached" in refused
    assert len(retriever.searches) == 1


async def test_a_chunk_found_by_two_searches_keeps_one_id():
    deps, ctx = make(FakeRetriever([passage(1)]))
    await search_filings(ctx, "first")
    second = await search_filings(ctx, "second")
    assert "[P1]" in second
    assert deps.evidence.ids() == {"P1"}


async def test_surrounding_chunks_are_registered_and_returned():
    retriever = FakeRetriever([passage(5)], neighbors=[passage(4), passage(6)])
    deps, ctx = make(retriever)
    await search_filings(ctx, "q")  # P1 is chunk 5
    shown = await read_surrounding_chunks(ctx, "P1")
    assert "[P2] " in shown and "[P3] " in shown
    assert "text 4" in shown and "text 6" in shown
    assert deps.evidence.ids() == {"P1", "P2", "P3"}


async def test_an_unknown_passage_id_asks_the_model_to_retry_with_valid_ids():
    _, ctx = make(FakeRetriever([passage(1)]))
    await search_filings(ctx, "q")
    with pytest.raises(ModelRetry, match="P99.*P1"):
        await read_surrounding_chunks(ctx, "P99")


@pytest.mark.parametrize(("asked", "used"), [(0, 1), (2, 2), (10, MAX_WINDOW)])
async def test_the_window_is_clamped_between_one_and_the_maximum(asked, used):
    retriever = FakeRetriever([passage(1)], neighbors=[passage(2)])
    _, ctx = make(retriever)
    await search_filings(ctx, "q")
    await read_surrounding_chunks(ctx, "P1", window=asked)
    assert retriever.window_asked == [used]


async def test_a_passage_without_neighbours_says_so():
    _, ctx = make(FakeRetriever([passage(1)], neighbors=[]))
    await search_filings(ctx, "q")
    assert "no neighbouring text" in await read_surrounding_chunks(ctx, "P1")


async def test_a_neighbour_already_seen_reuses_its_id():
    retriever = FakeRetriever([passage(1), passage(2)], neighbors=[passage(2)])
    deps, ctx = make(retriever)
    await search_filings(ctx, "q")  # P1 = chunk 1, P2 = chunk 2
    shown = await read_surrounding_chunks(ctx, "P1")
    assert "[P2]" in shown
    assert deps.evidence.ids() == {"P1", "P2"}
