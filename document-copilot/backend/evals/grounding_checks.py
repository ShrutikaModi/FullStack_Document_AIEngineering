"""Scoring for the grounding eval: did one real run of the agent behave as required?

No model, database or network in this file, so the rules themselves are unit tested
(tests/evals/test_grounding_checks.py). The runner (grounding_eval.py) collects a `RunRecord`
for the last question of a case and `check_run` returns what went wrong, or [].

The checks a case may use (all optional, set in grounding_cases.json under "checks"):

    enough_evidence        True / False: what the model must report
    no_searches            True: the model must answer without calling any tool
    cited_tickers_include  ["AAPL", ...]: each must appear among the cited passages
    searched_years_only    [2025]: every search that filters by year uses only these years
    searched_tickers_only  ["AAPL"]: every ticker filter used must be one of these
    must_match             ["391,035"]: each regex must be found in the answer
    must_match_any         [..]: at least one regex must be found
    must_not_match         [..]: none may be found
    max_chars              int: the answer may not be longer than this
    must_not_cite          ["P99"]: no citation may point at these passage ids
    accept_content_filter  True: Azure blocking the prompt counts as a pass
"""

import re
from dataclasses import dataclass, field

from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import Passage


@dataclass
class RunRecord:
    """Everything observed in one run of the final question of a case."""

    answer: GroundedAnswer | None = None
    # Set when the run produced no answer: "grounding_failed" or an error description.
    error: str | None = None
    searches: list[dict] = field(default_factory=list)  # arguments of each tool call
    cited: list[Passage] = field(default_factory=list)  # passages behind the citations
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    citation_retries: int = 0  # times the validator sent the answer back for fixing


def _found(patterns: list[str], text: str) -> list[str]:
    return [p for p in patterns if re.search(p, text, re.IGNORECASE)]


def check_run(checks: dict, run: RunRecord) -> list[str]:
    """Return a plain sentence for every check this run failed (empty list = pass)."""
    if (
        run.answer is None
        and checks.get("accept_content_filter")
        and (run.error or "").startswith("blocked")
    ):
        return []  # Azure refused the prompt: a valid defence, nothing was shown or saved
    if run.answer is None:
        return [f"no answer was produced ({run.error or 'unknown error'})"]

    failures: list[str] = []
    answer = run.answer
    text = answer.answer

    # Always: a cited answer must point at passages that can be shown with a page.
    for passage in run.cited:
        if passage.page is None:
            failures.append(
                f"cites {passage.company} FY{passage.fiscal_year} with no page number"
            )

    for citation in answer.citations:
        if citation.passage_id in checks.get("must_not_cite", []):
            failures.append(f"cites forbidden passage {citation.passage_id}")

    if (
        "enough_evidence" in checks
        and answer.enough_evidence != checks["enough_evidence"]
    ):
        failures.append(
            f"enough_evidence was {answer.enough_evidence}, expected {checks['enough_evidence']}"
        )
    if checks.get("no_searches") and run.searches:
        failures.append(f"searched {len(run.searches)} time(s) but should not have")

    cited_tickers = {p.ticker for p in run.cited}
    for ticker in checks.get("cited_tickers_include", []):
        if ticker not in cited_tickers:
            failures.append(
                f"no citation from {ticker} (cited: {sorted(cited_tickers)})"
            )

    years_allowed = checks.get("searched_years_only")
    if years_allowed:
        used = {y for s in run.searches for y in s.get("fiscal_years") or []}
        if not run.searches or not used or not used <= set(years_allowed):
            failures.append(
                f"searched fiscal years {sorted(used)}, expected {years_allowed}"
            )

    tickers_allowed = checks.get("searched_tickers_only")
    if tickers_allowed:
        used_tickers = {t for s in run.searches for t in s.get("tickers") or []}
        if not used_tickers <= set(tickers_allowed):
            failures.append(
                f"searched companies {sorted(used_tickers)}, expected only {tickers_allowed}"
            )

    for pattern in checks.get("must_match", []):
        if not re.search(pattern, text, re.IGNORECASE):
            failures.append(f"answer does not contain /{pattern}/")
    any_of = checks.get("must_match_any")
    if any_of and not _found(any_of, text):
        failures.append(f"answer contains none of {any_of}")
    for pattern in _found(checks.get("must_not_match", []), text):
        failures.append(f"answer contains forbidden /{pattern}/")
    if "max_chars" in checks and len(text) > checks["max_chars"]:
        failures.append(
            f"answer is {len(text)} characters, limit {checks['max_chars']}"
        )
    return failures
