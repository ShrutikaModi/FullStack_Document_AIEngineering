"""SQL for the two searches, plus loading the winners and their neighbours.

The two searches return only (chunk id, rank) so they stay cheap; the full text is
loaded once, after fusion, for the few chunks that made the final list.
"""

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncEngine

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.types import Passage, SearchFilters

CANDIDATES = 50  # how many results each search returns before fusion
# Length-normalised ts_rank (flag 1: divide by 1 + log(chunk length)). Tunable by the eval.
TS_RANK_FLAG = 1
WORD = re.compile(r"[a-z0-9]+")


# Words that describe the act of asking or the kind of document, not the topic. Every
# filing says "the Company" and "Form 10-K" many times, so as search words they match
# almost everything and push real answers down ("ITEM 16. FORM 10-K SUMMARY: None" once
# outranked the right passages). Postgres already drops ordinary stopwords (the, how, did).
FILLER_WORDS = frozenset(
    [
        "10k",
        "10ks",
        "form",
        "filing",
        "filings",
        "report",
        "latest",
        "summarize",
        "summary",
        "compare",
        "comparison",
        "describe",
        "describes",
        "described",
        "disclosed",
        "discloses",
        "disclose",
        "say",
        "says",
        "said",
        "mention",
        "identify",
        "explain",
        "important",
        "company",
        "companies",
        "fiscal",
        "year",
        "years",
    ]
)
TEN_K = re.compile(r"\b10-?ks?\b")


def build_or_query(question: str) -> str | None:
    """'How did Apple's revenue change?' -> 'how | did | apple | s | revenue | change'.

    websearch_to_tsquery would AND every word, so a full question would match almost
    nothing; OR lets any word match and the ranking puts chunks with most words first.
    Only letters and digits are kept, so no tsquery operator can be injected. Postgres
    (english config) drops stopwords and stems the words when it reads this.
    """
    words = [
        word
        for word in WORD.findall(TEN_K.sub(" ", question.lower()))
        if word not in FILLER_WORDS
    ]
    return " | ".join(words) if words else None


def _apply_filters(query: Select, filters: SearchFilters) -> Select:
    if filters.tickers:
        query = query.where(SourceDocument.ticker.in_(filters.tickers))
    if filters.fiscal_years:
        query = query.where(SourceDocument.fiscal_year.in_(filters.fiscal_years))
    if filters.section_prefix:
        query = query.where(DocumentChunk.section.startswith(filters.section_prefix))
    return query


def vector_query(embedding: list[float], filters: SearchFilters) -> Select:
    """Chunks closest in meaning to the question (cosine distance, HNSW index)."""
    distance = DocumentChunk.embedding.cosine_distance(embedding)
    query = (
        select(DocumentChunk.id)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)  # must match the index operator to use the index
        .limit(CANDIDATES)
    )
    return _apply_filters(query, filters)


def keyword_query(or_query: str, filters: SearchFilters) -> Select:
    """Chunks sharing the most words with the question (full-text, GIN index)."""
    tsquery = func.to_tsquery("english", or_query)
    rank = func.ts_rank(DocumentChunk.search_vector, tsquery, TS_RANK_FLAG)
    query = (
        select(DocumentChunk.id)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.search_vector.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.id)
        .limit(CANDIDATES)
    )
    return _apply_filters(query, filters)


async def vector_search(
    engine: AsyncEngine, embedding: list[float], filters: SearchFilters
) -> list[UUID]:
    async with engine.connect() as connection:
        # Without this, a filter is applied after the index returns ~40 rows and can
        # leave far fewer than CANDIDATES. Lasts only for this transaction.
        await connection.execute(
            text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")
        )
        result = await connection.execute(vector_query(embedding, filters))
        return list(result.scalars())


async def keyword_search(
    engine: AsyncEngine, question: str, filters: SearchFilters
) -> list[UUID]:
    or_query = build_or_query(question)
    if or_query is None:
        return []
    async with engine.connect() as connection:
        result = await connection.execute(keyword_query(or_query, filters))
        return list(result.scalars())


_PASSAGE_COLUMNS = (
    DocumentChunk.id,
    DocumentChunk.document_id,
    DocumentChunk.chunk_index,
    SourceDocument.ticker,
    SourceDocument.company,
    SourceDocument.form_type,
    SourceDocument.fiscal_year,
    SourceDocument.filing_date,
    SourceDocument.source_url,
    DocumentChunk.page,
    DocumentChunk.section,
    DocumentChunk.content,
)


def _passage(row) -> Passage:
    return Passage(*row)


async def load_passages(
    engine: AsyncEngine, chunk_ids: list[UUID]
) -> dict[UUID, Passage]:
    """Full text and filing details for the given chunks."""
    if not chunk_ids:
        return {}
    query = (
        select(*_PASSAGE_COLUMNS)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids))
    )
    async with engine.connect() as connection:
        rows = (await connection.execute(query)).all()
    return {row.id: _passage(row) for row in rows}


@dataclass(frozen=True)
class Position:
    document_id: UUID
    chunk_index: int


async def load_neighbors(
    engine: AsyncEngine, positions: list[Position]
) -> dict[Position, Passage]:
    """Chunks at the given spots (filing + chunk number), e.g. the ones next to a hit."""
    if not positions:
        return {}
    query = (
        select(*_PASSAGE_COLUMNS)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(
            tuple_(DocumentChunk.document_id, DocumentChunk.chunk_index).in_(
                [(p.document_id, p.chunk_index) for p in positions]
            )
        )
    )
    async with engine.connect() as connection:
        rows = (await connection.execute(query)).all()
    return {Position(row.document_id, row.chunk_index): _passage(row) for row in rows}
