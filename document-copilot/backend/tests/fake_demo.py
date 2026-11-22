"""A small stand-in for the recorded examples, so demo tests do not depend on the real data."""

from uuid import uuid4

from app.demo.examples import DemoExample

QUESTION = "What was Apple's total net sales in fiscal 2024?"

FAKE_EXAMPLE = DemoExample(
    id="fake-apple",
    company="Apple",
    kind="Single figure",
    question=QUESTION,
    steps=["Searching AAPL FY2024 filings: total net sales"],
    answer="Apple's total net sales were $391,035 million in fiscal 2024 [1].",
    sources=[
        {
            "label": 1,
            "chunkId": str(uuid4()),
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "formType": "10-K",
            "fiscalYear": 2024,
            "filingDate": "2024-11-01",
            "page": 28,
            "section": "Item 7",
            "excerpt": "Total net sales | 391,035 | 383,285",
            "sourceUrl": "https://www.sec.gov/example",
        }
    ],
)


def use_fake_example(monkeypatch) -> None:
    """Make the demo code see only FAKE_EXAMPLE (each module imported EXAMPLES by name)."""
    monkeypatch.setattr("app.demo.examples.EXAMPLES", [FAKE_EXAMPLE])
    monkeypatch.setattr("app.api.chat.EXAMPLES", [FAKE_EXAMPLE])
    monkeypatch.setattr("app.chat.demo_turn.STEP_PAUSE_SECONDS", 0)
    monkeypatch.setattr("app.chat.demo_turn.PIECE_PAUSE_SECONDS", 0)
