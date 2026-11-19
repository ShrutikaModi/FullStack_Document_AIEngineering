import json
from datetime import date
from uuid import UUID

import pytest

from app.retrieval.types import Passage, SearchFilters
from evals.retrieval_eval import GOLDEN, first_hit, matches, summarize


def passage(content="x", ticker="AAPL", year=2024, section="Item 7. MD&A") -> Passage:
    return Passage(
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        chunk_index=0,
        ticker=ticker,
        company="c",
        form_type="10-K",
        fiscal_year=year,
        filing_date=date(2024, 1, 1),
        source_url="u",
        page=1,
        section=section,
        content=content,
    )


def test_a_passage_must_meet_every_condition():
    expect = {
        "tickers": ["AAPL"],
        "fiscal_years": [2024],
        "section_prefix": "Item 7",
        "contains": ["iphone"],
    }
    assert matches(passage("iPhone sales rose"), expect)
    assert not matches(passage("iPhone sales rose", ticker="MSFT"), expect)
    assert not matches(passage("iPhone sales rose", year=2021), expect)
    assert not matches(passage("iPhone sales rose", section="Item 1A. Risk"), expect)
    assert not matches(passage("Mac sales rose"), expect)


def test_any_one_phrase_is_enough_and_case_does_not_matter():
    assert matches(
        passage("Supply Constraints"),
        {"contains": ["limited number of", "supply constraints"]},
    )


def test_conditions_left_out_are_not_checked():
    assert matches(passage("cloud", section=None), {"contains": ["cloud"]})


def test_first_hit_is_a_one_based_position_or_none():
    expect = {"contains": ["target"]}
    assert first_hit([passage("a"), passage("target"), passage("target")], expect) == 2
    assert first_hit([passage("a"), passage("b")], expect) is None
    assert first_hit([], expect) is None


def test_summary_scores():
    s = summarize([1, 4, 8, None])
    assert s["hit@5"] == 0.5
    assert s["hit@10"] == 0.75
    assert s["mrr"] == pytest.approx((1 + 1 / 4 + 1 / 8) / 4)


def test_every_golden_question_is_well_formed():
    golden = json.loads(GOLDEN.read_text())
    assert len({q["id"] for q in golden}) == len(golden)
    for q in golden:
        assert q["kind"] in {"brief", "exact"}
        SearchFilters(**q["filters"])  # filter keys must be real ones
        assert q["expect"]["contains"], q["id"]
        assert set(q["expect"]) <= {
            "tickers",
            "fiscal_years",
            "section_prefix",
            "contains",
        }
