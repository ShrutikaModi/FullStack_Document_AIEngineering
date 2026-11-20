import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings
from app.retrieval import queries
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import Position
from app.retrieval.types import Passage, SearchFilters

Embedder = Callable[[str], Awaitable[list[float]]]

DEFAULT_TOP_K = 8
DEFAULT_NEIGHBORS = 1


def openai_embedder(client: AsyncOpenAI) -> Embedder:
    """Turns a question into the same kind of vector the filings were stored with."""

    async def embed(question: str) -> list[float]:
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            input=question,
        )
        return response.data[0].embedding

    return embed


class DocumentRetriever:
    """Question in, the best matching filing passages out (hybrid search).

    Meaning search and keyword search run side by side; their two ranked lists are
    merged with Reciprocal Rank Fusion. Both inputs are passed in so tests can fake them.
    """

    def __init__(self, engine: AsyncEngine, embed: Embedder) -> None:
        self._engine = engine
        self._embed = embed

    async def search(
        self,
        question: str,
        filters: SearchFilters | None = None,
        top_k: int = DEFAULT_TOP_K,
        neighbors: int = DEFAULT_NEIGHBORS,
    ) -> list[Passage]:
        filters = filters or SearchFilters()
        embedding = await self._embed(question)
        vector_ids, keyword_ids = await asyncio.gather(
            queries.vector_search(self._engine, embedding, filters),
            queries.keyword_search(self._engine, question, filters),
        )

        best = reciprocal_rank_fusion([vector_ids, keyword_ids])[:top_k]
        if not best:
            return []

        loaded = await queries.load_passages(
            self._engine, [chunk_id for chunk_id, _ in best]
        )
        vector_rank = {
            chunk_id: rank for rank, chunk_id in enumerate(vector_ids, start=1)
        }
        keyword_rank = {
            chunk_id: rank for rank, chunk_id in enumerate(keyword_ids, start=1)
        }
        passages = [
            replace(
                loaded[chunk_id],
                score=score,
                vector_rank=vector_rank.get(chunk_id),
                keyword_rank=keyword_rank.get(chunk_id),
            )
            for chunk_id, score in best
        ]
        return await self.attach_neighbors(passages, neighbors)

    async def attach_neighbors(
        self, passages: list[Passage], window: int
    ) -> list[Passage]:
        """Add the chunks just before and after each result (same filing, reading order)."""
        if window <= 0:
            return passages
        known = {Position(p.document_id, p.chunk_index): p for p in passages}
        wanted = {
            Position(p.document_id, p.chunk_index + offset)
            for p in passages
            for offset in range(-window, window + 1)
            if offset != 0 and p.chunk_index + offset >= 0
        }
        fetched = await queries.load_neighbors(
            self._engine, sorted_positions(wanted - known.keys())
        )
        pool = {
            **fetched,
            **known,
        }  # a result that is also a neighbour is reused, not refetched
        return [
            replace(
                p,
                neighbors=tuple(
                    pool[position]
                    for offset in range(-window, window + 1)
                    if offset != 0
                    and (position := Position(p.document_id, p.chunk_index + offset))
                    in pool
                ),
            )
            for p in passages
        ]


def sorted_positions(positions: set[Position]) -> list[Position]:
    return sorted(positions, key=lambda p: (str(p.document_id), p.chunk_index))
