"""Measure how well search finds the right passages, for three methods side by side.

Run from backend/:  uv run python -m evals.retrieval_eval

For each question in golden_questions.json the script runs keyword-only, meaning-only
(vector) and hybrid search, and records at which position the first correct passage
appears (a "hit"). It then reports hit@5, hit@10 and the average of 1/position (MRR).
A passage is correct when it matches every condition in the question's "expect" block:
company, fiscal year and section prefix (when given) and at least one of the phrases.
"""

import asyncio
import json
from pathlib import Path

from app.database.engine import create_db_engine
from app.openai_client import create_async_openai_client
from app.retrieval import queries
from app.retrieval.retriever import DocumentRetriever, Embedder, openai_embedder
from app.retrieval.types import Passage, SearchFilters

GOLDEN = Path(__file__).parent / "golden_questions.json"
METHODS = ("keyword", "vector", "hybrid")
TOP_K = 10


def matches(passage: Passage, expect: dict) -> bool:
    """True if the passage meets every condition in the question's expectation."""
    if expect.get("tickers") and passage.ticker not in expect["tickers"]:
        return False
    if expect.get("fiscal_years") and passage.fiscal_year not in expect["fiscal_years"]:
        return False
    prefix = expect.get("section_prefix")
    if prefix and not (passage.section or "").startswith(prefix):
        return False
    text = passage.content.lower()
    return any(phrase.lower() in text for phrase in expect["contains"])


def first_hit(passages: list[Passage], expect: dict) -> int | None:
    """1-based position of the first correct passage, or None."""
    for position, passage in enumerate(passages, start=1):
        if matches(passage, expect):
            return position
    return None


def summarize(ranks: list[int | None]) -> dict[str, float]:
    total = len(ranks)
    return {
        "hit@5": sum(1 for r in ranks if r and r <= 5) / total,
        "hit@10": sum(1 for r in ranks if r and r <= 10) / total,
        "mrr": sum(1 / r for r in ranks if r) / total,
    }


def cached(embed: Embedder) -> Embedder:
    """Each question is embedded once and reused by the vector and hybrid runs."""
    seen: dict[str, list[float]] = {}

    async def embed_once(question: str) -> list[float]:
        if question not in seen:
            seen[question] = await embed(question)
        return seen[question]

    return embed_once


async def run(golden: list[dict]) -> dict[str, dict[str, int | None]]:
    engine = create_db_engine()
    embed = cached(openai_embedder(create_async_openai_client()))
    retriever = DocumentRetriever(engine, embed)
    ranks: dict[str, dict[str, int | None]] = {}
    try:
        for item in golden:
            question, expect = item["question"], item["expect"]
            filters = SearchFilters(**item["filters"])
            embedding = await embed(question)
            id_lists = {
                "keyword": (await queries.keyword_search(engine, question, filters))[
                    :TOP_K
                ],
                "vector": (await queries.vector_search(engine, embedding, filters))[
                    :TOP_K
                ],
            }
            loaded = await queries.load_passages(
                engine, [i for ids in id_lists.values() for i in ids]
            )
            hybrid = await retriever.search(question, filters, top_k=TOP_K, neighbors=0)
            ranks[item["id"]] = {
                "keyword": first_hit([loaded[i] for i in id_lists["keyword"]], expect),
                "vector": first_hit([loaded[i] for i in id_lists["vector"]], expect),
                "hybrid": first_hit(hybrid, expect),
            }
    finally:
        await engine.dispose()
    return ranks


def report(golden: list[dict], ranks: dict[str, dict[str, int | None]]) -> None:
    print(f"\n{'question':40} {'kind':6}" + "".join(f"{m:>9}" for m in METHODS))
    print(
        "(number = position of the first correct passage in the top 10; - = not found)"
    )
    for item in golden:
        row = ranks[item["id"]]
        cells = "".join(f"{(row[m] or '-')!s:>9}" for m in METHODS)
        print(f"{item['id'][:40]:40} {item['kind']:6}{cells}")

    for label, kinds in (
        ("ALL", {"brief", "exact"}),
        ("brief", {"brief"}),
        ("exact", {"exact"}),
    ):
        chosen = [i["id"] for i in golden if i["kind"] in kinds]
        print(f"\n{label} ({len(chosen)} questions)")
        print(f"{'method':10}{'hit@5':>8}{'hit@10':>8}{'mrr':>8}")
        for method in METHODS:
            s = summarize([ranks[i][method] for i in chosen])
            print(f"{method:10}{s['hit@5']:>8.0%}{s['hit@10']:>8.0%}{s['mrr']:>8.2f}")


if __name__ == "__main__":
    golden_questions = json.loads(GOLDEN.read_text())
    report(golden_questions, asyncio.run(run(golden_questions)))
