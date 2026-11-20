from datetime import date
from uuid import UUID

from app.assistant.deps import EvidenceLog
from app.retrieval.types import Passage


def passage(n: int) -> Passage:
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
        page=n,
        section="Item 7",
        content=f"text {n}",
    )


def test_ids_start_at_p1_and_count_up():
    log = EvidenceLog()
    assert [log.add(passage(n)) for n in (1, 2, 3)] == ["P1", "P2", "P3"]


def test_the_same_chunk_always_gets_the_same_id():
    log = EvidenceLog()
    first = log.add(passage(1))
    log.add(passage(2))
    assert log.add(passage(1)) == first == "P1"
    assert log.ids() == {"P1", "P2"}


def test_ids_lists_exactly_what_was_added():
    log = EvidenceLog()
    assert log.ids() == set()
    log.add(passage(5))
    assert log.ids() == {"P1"}


def test_a_new_log_is_empty_so_nothing_carries_over_between_questions():
    first, second = EvidenceLog(), EvidenceLog()
    first.add(passage(1))
    assert second.ids() == set()
    assert second.get("P1") is None


def test_get_returns_the_passage_or_none():
    log = EvidenceLog()
    log.add(passage(7))
    assert log.get("P1").content == "text 7"
    assert log.get("P2") is None
