from datetime import date
from uuid import UUID

from app.assistant.deps import EvidenceLog
from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.sources import MAX_EXCERPT_CHARS, build_sources
from app.retrieval.types import Passage


def passage(content: str) -> Passage:
    return Passage(
        chunk_id=UUID(int=1),
        document_id=UUID(int=9),
        chunk_index=1,
        ticker="NVDA",
        company="NVIDIA Corporation",
        form_type="10-K",
        fiscal_year=2025,
        filing_date=date(2025, 2, 26),
        source_url="https://www.sec.gov/example",
        page=41,
        section="Item 7",
        content=content,
    )


def cited(content: str) -> dict:
    evidence = EvidenceLog()
    evidence.add(passage(content))
    answer = GroundedAnswer(
        answer="x [1].",
        citations=[Citation(label=1, passage_id="P1")],
        enough_evidence=True,
    )
    return build_sources(answer, evidence)[0]


def test_a_long_passage_is_shown_in_full_so_the_cited_sentence_is_visible():
    # The longest stored chunk is about 4,300 characters; the proof can be at the very end.
    content = "x" * 4300 + " customers which represented 10% or more of total revenue"
    assert cited(content)["excerpt"] == content


def test_an_absurdly_long_passage_is_still_cut():
    assert len(cited("x" * (MAX_EXCERPT_CHARS + 500))["excerpt"]) == MAX_EXCERPT_CHARS
