from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.retrieval import queries, retriever
from app.retrieval.queries import Position
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import Passage, SearchFilters

pytestmark = pytest.mark.anyio

DOC = UUID(int=999)


def chunk_id(n: int) -> UUID:
    return UUID(int=n)


def passage(n: int, index: int | None = None, document: UUID = DOC) -> Passage:
    return Passage(
        chunk_id=chunk_id(n),
        document_id=document,
        chunk_index=n if index is None else index,
        ticker="AAPL",
        company="Apple Inc.",
        form_type="10-K",
        fiscal_year=2024,
        filing_date=date(2024, 11, 1),
        source_url="https://example.test/f",
        page=n,
        section="Item 1A. Risk Factors",
        content=f"text {n}",
    )


class Recorder:
    """Stands in for the database layer and remembers how it was called."""

    def __init__(self, vector_ids, keyword_ids, corpus):
        self.vector_ids, self.keyword_ids = vector_ids, keyword_ids
        self.corpus = {p.chunk_id: p for p in corpus}
        self.calls: dict[str, object] = {}

    async def vector_search(self, engine, embedding, filters):
        self.calls["vector"] = (embedding, filters)
        return self.vector_ids

    async def keyword_search(self, engine, question, filters):
        self.calls["keyword"] = (question, filters)
        return self.keyword_ids

    async def load_passages(self, engine, ids):
        self.calls["load"] = list(ids)
        return {i: self.corpus[i] for i in ids}

    async def load_neighbors(self, engine, positions):
        self.calls["neighbors"] = list(positions)
        by_position = {
            Position(p.document_id, p.chunk_index): p for p in self.corpus.values()
        }
        return {pos: by_position[pos] for pos in positions if pos in by_position}


@pytest.fixture
def wire(monkeypatch):
    def _wire(vector_ids, keyword_ids, corpus):
        fake = Recorder(vector_ids, keyword_ids, corpus)
        for name in (
            "vector_search",
            "keyword_search",
            "load_passages",
            "load_neighbors",
        ):
            monkeypatch.setattr(queries, name, getattr(fake, name))
        return fake

    return _wire


async def embed(question: str) -> list[float]:
    return [0.5, 0.5]


def make() -> DocumentRetriever:
    return DocumentRetriever(engine=object(), embed=embed)


async def test_results_are_the_fused_order_with_ranks_attached(wire):
    # 1 is rank 1 in both lists, 2 only vector rank 2, 3 only keyword rank 2.
    wire(
        [chunk_id(1), chunk_id(2)],
        [chunk_id(1), chunk_id(3)],
        [passage(1), passage(2), passage(3)],
    )
    results = await make().search("q", neighbors=0)
    assert [p.chunk_id for p in results] == [chunk_id(1), chunk_id(2), chunk_id(3)]
    first = results[0]
    assert (first.vector_rank, first.keyword_rank) == (1, 1)
    assert (results[1].vector_rank, results[1].keyword_rank) == (2, None)
    assert (results[2].vector_rank, results[2].keyword_rank) == (None, 2)
    assert first.score > results[1].score


async def test_only_top_k_results_are_loaded_and_returned(wire):
    ids = [chunk_id(n) for n in range(1, 21)]
    fake = wire(ids, [], [passage(n) for n in range(1, 21)])
    results = await make().search("q", top_k=5, neighbors=0)
    assert [p.chunk_id for p in results] == ids[:5]
    assert fake.calls["load"] == ids[:5]


async def test_question_and_filters_reach_both_searches(wire):
    fake = wire([chunk_id(1)], [chunk_id(1)], [passage(1)])
    filters = SearchFilters(tickers=["MSFT"], fiscal_years=[2023])
    await make().search("azure growth", filters, neighbors=0)
    assert fake.calls["vector"] == ([0.5, 0.5], filters)
    assert fake.calls["keyword"] == ("azure growth", filters)


async def test_no_matches_returns_nothing_and_loads_nothing(wire):
    fake = wire([], [], [])
    assert await make().search("q") == []
    assert "load" not in fake.calls


async def test_neighbors_are_the_chunks_before_and_after_in_reading_order(wire):
    corpus = [passage(n) for n in range(1, 8)]
    wire([chunk_id(4)], [], corpus)
    (result,) = await make().search("q", neighbors=1)
    assert [p.chunk_index for p in result.neighbors] == [3, 5]


async def test_larger_window_gets_more_context(wire):
    wire([chunk_id(4)], [], [passage(n) for n in range(1, 8)])
    (result,) = await make().search("q", neighbors=2)
    assert [p.chunk_index for p in result.neighbors] == [2, 3, 5, 6]


async def test_first_chunk_of_a_filing_has_no_negative_neighbor(wire):
    fake = wire([chunk_id(0)], [], [passage(0), passage(1)])
    (result,) = await make().search("q", neighbors=1)
    assert [p.chunk_index for p in result.neighbors] == [1]
    assert all(pos.chunk_index >= 0 for pos in fake.calls["neighbors"])


async def test_a_result_that_is_also_a_neighbor_is_not_fetched_again(wire):
    fake = wire([chunk_id(4), chunk_id(5)], [], [passage(n) for n in range(1, 8)])
    results = await make().search("q", neighbors=1)
    fetched = {pos.chunk_index for pos in fake.calls["neighbors"]}
    assert fetched == {3, 6}  # 4 and 5 are already in hand
    assert [p.chunk_index for p in results[0].neighbors] == [3, 5]
    assert [p.chunk_index for p in results[1].neighbors] == [4, 6]


async def test_neighbors_stay_inside_their_own_filing(wire):
    other = UUID(int=555)
    corpus = [passage(1, index=4), passage(2, index=5, document=other)]
    wire([chunk_id(1)], [], corpus)
    (result,) = await make().search("q", neighbors=1)
    assert result.neighbors == ()  # chunk 5 exists, but in a different filing


async def test_zero_window_skips_the_neighbor_query(wire):
    fake = wire([chunk_id(1)], [], [passage(1)])
    await make().search("q", neighbors=0)
    assert "neighbors" not in fake.calls


async def test_the_question_is_embedded_once(wire):
    wire([chunk_id(1)], [], [passage(1)])
    seen: list[str] = []

    async def spy(question: str) -> list[float]:
        seen.append(question)
        return [0.0]

    await DocumentRetriever(engine=object(), embed=spy).search("what changed?")
    assert seen == ["what changed?"]


async def test_openai_embedder_returns_the_vector_from_the_api():
    calls: list[dict] = []

    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])

    client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    result = await retriever.openai_embedder(client)("hello")
    assert result == [0.1, 0.2]
    assert calls[0]["input"] == "hello"
