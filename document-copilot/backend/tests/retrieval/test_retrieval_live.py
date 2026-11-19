"""Real searches against the ingested filings (needs Supabase and the OpenAI/Azure key).

Skipped by default. Run with:  uv run pytest -m integration
"""

import pytest

from app.database.engine import create_db_engine
from app.openai_client import create_async_openai_client
from app.retrieval.retriever import DocumentRetriever, openai_embedder
from app.retrieval.types import SearchFilters

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


@pytest.fixture
async def retriever():
    engine = create_db_engine()
    yield DocumentRetriever(engine, openai_embedder(create_async_openai_client()))
    await engine.dispose()


async def test_a_company_question_returns_citable_passages_from_that_company(retriever):
    results = await retriever.search(
        "How did Apple's iPhone revenue mix change?", SearchFilters(tickers=["AAPL"])
    )
    assert len(results) == 8
    for passage in results:
        assert passage.ticker == "AAPL"
        assert passage.page is not None  # every passage can be cited with a page
        assert passage.section
        assert passage.content.strip()
        assert passage.source_url.startswith("https://www.sec.gov/")


async def test_results_are_ordered_by_score_and_show_which_search_found_them(retriever):
    results = await retriever.search("NVIDIA Data Center supply constraints")
    scores = [p.score for p in results]
    assert scores == sorted(scores, reverse=True)
    assert all(p.score > 0 for p in results)
    assert all(p.vector_rank or p.keyword_rank for p in results)


async def test_filters_keep_other_companies_years_and_sections_out(retriever):
    filters = SearchFilters(
        tickers=["MSFT"], fiscal_years=[2023], section_prefix="Item 1A"
    )
    results = await retriever.search("cloud and AI risks", filters)
    assert results
    for passage in results:
        assert (passage.ticker, passage.fiscal_year) == ("MSFT", 2023)
        assert passage.section.startswith("Item 1A")


async def test_neighbors_are_the_adjacent_chunks_of_the_same_filing(retriever):
    results = await retriever.search("Tesla Gigafactory Shanghai", neighbors=1)
    for passage in results:
        assert 1 <= len(passage.neighbors) <= 2
        for neighbor in passage.neighbors:
            assert neighbor.document_id == passage.document_id
            assert abs(neighbor.chunk_index - passage.chunk_index) == 1


async def test_an_exact_term_is_found_at_the_top(retriever):
    results = await retriever.search("Tesla Gigafactory Shanghai", neighbors=0)
    assert "Gigafactory Shanghai" in results[0].content


async def test_a_filter_matching_nothing_returns_no_results(retriever):
    assert await retriever.search("revenue", SearchFilters(tickers=["NOSUCH"])) == []
