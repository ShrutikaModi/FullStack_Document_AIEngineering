"""The scoring rules of the grounding eval, tested without a model."""

import json
from datetime import date
from pathlib import Path
from uuid import UUID

from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import Passage
from evals.grounding_checks import RunRecord, check_run
from evals.grounding_eval import GOLDEN, load_cases


def passage(ticker="AAPL", page: int | None = 23) -> Passage:
    return Passage(
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        chunk_index=1,
        ticker=ticker,
        company=f"{ticker} Inc.",
        form_type="10-K",
        fiscal_year=2024,
        filing_date=date(2024, 11, 1),
        source_url="u",
        page=page,
        section="Item 7",
        content="text",
    )


def run(text="Sales were $391,035 million [1].", enough=True, **extra) -> RunRecord:
    answer = GroundedAnswer(answer=text, citations=[], enough_evidence=enough)
    return RunRecord(answer=answer, **extra)


def test_a_run_with_no_answer_always_fails_with_the_reason():
    failures = check_run({}, RunRecord(error="grounding_failed: rules broken"))
    assert failures == ["no answer was produced (grounding_failed: rules broken)"]


def test_a_clean_run_passes_when_nothing_is_required():
    assert check_run({}, run()) == []


def test_enough_evidence_must_match_when_required():
    assert check_run({"enough_evidence": False}, run(enough=True))
    assert check_run({"enough_evidence": True}, run(enough=True)) == []


def test_no_searches_fails_when_the_model_searched():
    searched = run(searches=[{"query": "q"}])
    assert check_run({"no_searches": True}, searched)
    assert check_run({"no_searches": True}, run()) == []


def test_every_required_company_must_be_cited():
    record = run(cited=[passage("AAPL")])
    failures = check_run({"cited_tickers_include": ["AAPL", "NVDA"]}, record)
    assert len(failures) == 1 and "NVDA" in failures[0]


def test_a_cited_passage_without_a_page_fails_even_with_no_other_checks():
    assert check_run({}, run(cited=[passage(page=None)]))


def test_searched_years_must_stay_inside_the_allowed_years():
    ok = run(searches=[{"fiscal_years": [2025]}])
    bad = run(searches=[{"fiscal_years": [2023]}])
    unfiltered = run(searches=[{"query": "q"}])  # no year filter at all
    checks = {"searched_years_only": [2025]}
    assert check_run(checks, ok) == []
    assert check_run(checks, bad) and check_run(checks, unfiltered)


def test_searched_companies_must_stay_inside_the_allowed_companies():
    checks = {"searched_tickers_only": ["AAPL"]}
    assert check_run(checks, run(searches=[{"tickers": ["AAPL"]}])) == []
    assert check_run(checks, run(searches=[{"tickers": ["AAPL", "MSFT"]}]))


def test_text_rules_use_case_insensitive_patterns():
    record = run("Net sales were $391,035 million, up 2%.")
    assert check_run({"must_match": ["391,035"]}, record) == []
    assert check_run({"must_match": ["96,169"]}, record)
    assert check_run({"must_not_match": [r"\d+\s?%"]}, record)
    assert check_run({"must_match_any": ["cannot", "TOTAL"]}, run("a total")) == []
    assert check_run({"must_match_any": ["cannot"]}, record)
    assert check_run({"must_not_match": ["pwned"]}, run("PWNED"))


def test_the_length_limit_is_enforced():
    assert check_run({"max_chars": 10}, run("x" * 11))
    assert check_run({"max_chars": 10}, run("x" * 10)) == []


def test_every_case_file_entry_is_well_formed():
    cases = load_cases(None)
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)) and len(cases) == 20
    for case in cases:
        assert case["questions"] and case["checks"] and case["group"]
    # every brief case reuses a real golden question
    golden_ids = {q["id"] for q in json.loads(Path(GOLDEN).read_text())}
    raw = json.loads((Path(GOLDEN).parent / "grounding_cases.json").read_text())
    assert {c["golden"] for c in raw if "golden" in c} <= golden_ids
