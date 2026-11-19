from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.retrieval import queries
from app.retrieval.queries import (
    CANDIDATES,
    build_or_query,
    keyword_query,
    vector_query,
)
from app.retrieval.types import SearchFilters

pytestmark = pytest.mark.anyio

NO_FILTERS = SearchFilters()


def sql(query) -> str:
    return str(query.compile(dialect=postgresql.dialect()))


# ---- OR query -------------------------------------------------------------------


def test_or_query_joins_every_word_with_or():
    assert build_or_query("How did Apple's iPhone revenue change?") == (
        "how | did | apple | s | iphone | revenue | change"
    )


def test_or_query_keeps_digits_and_lowercases():
    assert build_or_query("AWS 2024 margin") == "aws | 2024 | margin"


def test_or_query_strips_characters_that_are_tsquery_operators():
    assert build_or_query("revenue & (cloud) | !risk :* <-> x'; drop table") == (
        "revenue | cloud | risk | x | drop | table"
    )


def test_filler_words_about_the_document_are_left_out():
    assert build_or_query(
        "Summarize the geographic exposures in the latest 10-K filings"
    ) == ("the | geographic | exposures | in | the")


def test_item_10_is_not_mistaken_for_form_10_k():
    assert build_or_query("Item 10 directors") == "item | 10 | directors"


def test_a_question_made_only_of_filler_words_has_no_query():
    assert build_or_query("Summarize the latest filings") == "the"
    assert build_or_query("summarize latest 10-K filings") is None


@pytest.mark.parametrize("text", ["", "   ", "?!&|()", "—…"])
def test_or_query_is_none_when_there_are_no_words(text):
    assert build_or_query(text) is None


# ---- query assembly -------------------------------------------------------------


def test_vector_query_orders_by_cosine_distance_and_limits():
    text = sql(vector_query([0.1] * 1536, NO_FILTERS))
    assert "<=>" in text
    assert "embedding IS NOT NULL" in text
    assert "ORDER BY document_chunks.embedding <=>" in text
    assert "LIMIT" in text
    assert vector_query([0.1] * 1536, NO_FILTERS)._limit == CANDIDATES


def test_keyword_query_matches_with_tsquery_and_ranks():
    text = sql(keyword_query("revenue | cloud", NO_FILTERS))
    assert "to_tsquery" in text
    assert "@@" in text
    assert "ts_rank" in text
    assert keyword_query("revenue | cloud", NO_FILTERS)._limit == CANDIDATES


@pytest.mark.parametrize(
    "builder",
    [
        lambda f: vector_query([0.0] * 1536, f),
        lambda f: keyword_query("revenue", f),
    ],
)
def test_no_filters_means_no_where_clauses_for_them(builder):
    text = sql(builder(NO_FILTERS))
    assert "source_documents.ticker" not in text
    assert "fiscal_year" not in text
    assert "LIKE" not in text


@pytest.mark.parametrize(
    "builder",
    [
        lambda f: vector_query([0.0] * 1536, f),
        lambda f: keyword_query("revenue", f),
    ],
)
def test_each_filter_is_applied_to_both_searches(builder):
    filters = SearchFilters(
        tickers=["AAPL"], fiscal_years=[2023, 2024], section_prefix="Item 1A"
    )
    text = sql(builder(filters))
    assert "source_documents.ticker IN" in text
    assert "source_documents.fiscal_year IN" in text
    assert "document_chunks.section LIKE" in text


def test_filter_values_are_bound_not_pasted_into_the_sql():
    evil = "AAPL'; DROP TABLE x;--"
    query = keyword_query("revenue", SearchFilters(tickers=[evil]))
    assert "DROP TABLE" not in sql(query)
    bound = query.compile(dialect=postgresql.dialect()).params
    assert [evil] in bound.values()


# ---- running the searches (fake engine records what is sent) --------------------


class FakeResult:
    def __init__(self, ids):
        self._ids = ids

    def scalars(self):
        return iter(self._ids)


class FakeConnection:
    def __init__(self, log, ids):
        self.log, self.ids = log, ids

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, statement):
        self.log.append(str(statement))
        return FakeResult(self.ids)


class FakeEngine:
    def __init__(self, ids=()):
        self.log: list[str] = []
        self.ids = list(ids)

    def connect(self):
        return FakeConnection(self.log, self.ids)


async def test_vector_search_sets_iterative_scan_before_the_query():
    ids = [UUID(int=1), UUID(int=2)]
    engine = FakeEngine(ids)
    result = await queries.vector_search(engine, [0.0] * 1536, NO_FILTERS)
    assert result == ids
    assert "hnsw.iterative_scan" in engine.log[0]
    assert "<=>" in engine.log[1]


async def test_keyword_search_skips_the_database_when_the_question_has_no_words():
    engine = FakeEngine([UUID(int=1)])
    assert await queries.keyword_search(engine, "?!", NO_FILTERS) == []
    assert engine.log == []


async def test_keyword_search_runs_one_query():
    ids = [UUID(int=7)]
    engine = FakeEngine(ids)
    assert await queries.keyword_search(engine, "cloud revenue", NO_FILTERS) == ids
    assert len(engine.log) == 1


async def test_loading_nothing_does_not_touch_the_database():
    engine = FakeEngine()
    assert await queries.load_passages(engine, []) == {}
    assert await queries.load_neighbors(engine, []) == {}
    assert engine.log == []
