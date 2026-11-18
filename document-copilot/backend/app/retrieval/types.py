from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class SearchFilters:
    """Optional limits; an empty value means "don't filter on this"."""

    tickers: list[str] = field(default_factory=list)  # e.g. ["AAPL"]
    fiscal_years: list[int] = field(default_factory=list)  # e.g. [2023, 2024]
    section_prefix: str | None = None  # e.g. "Item 1A" matches "Item 1A. Risk Factors"


@dataclass(frozen=True)
class Passage:
    """One chunk of a filing, with what is needed to cite it."""

    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    ticker: str
    company: str
    form_type: str
    fiscal_year: int
    filing_date: date
    source_url: str
    page: int | None
    section: str | None
    content: str
    # How the searches ranked it (1 = best); None if that search didn't return it.
    vector_rank: int | None = None
    keyword_rank: int | None = None
    score: float = 0.0
    # The chunks just before and after it in the same filing, for extra context.
    neighbors: tuple["Passage", ...] = ()
