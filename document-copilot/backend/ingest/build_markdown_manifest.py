"""Write data/markdown/manifest.json: one entry per converted filing.

Run from backend/:  uv run python ingest/build_markdown_manifest.py

Takes the filing facts from data/downloads/manifest.json and adds the company
name, fiscal year and the path of the Markdown file, so later steps (chunking,
loading into the database) have everything they need in one place.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOWNLOADS_MANIFEST = DATA_DIR / "downloads" / "manifest.json"
MARKDOWN = DATA_DIR / "markdown"

COMPANIES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "META": "Meta Platforms, Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla, Inc.",
}


def main() -> None:
    downloads = json.loads(DOWNLOADS_MANIFEST.read_text())
    filings = []
    for filing in downloads["filings"]:
        markdown_path = Path(filing["local_path"]).with_suffix(".md")
        file = MARKDOWN / markdown_path
        if not file.exists():
            raise SystemExit(
                f"Missing Markdown file: {file} (run to_markdown.py first)"
            )
        filings.append(
            {
                "ticker": filing["ticker"],
                "company": COMPANIES[filing["ticker"]],
                "form": filing["form"],
                "fiscal_year": int(filing["report_date"][:4]),
                "report_date": filing["report_date"],
                "filing_date": filing["filing_date"],
                "accession_number": filing["accession_number"],
                "source_url": filing["source_url"],
                "markdown_path": markdown_path.as_posix(),
                "size_bytes": file.stat().st_size,
            }
        )

    manifest = {
        "source": "Docling conversion of data/downloads",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "form": downloads["form"],
        "markdown_count": len(filings),
        "filings": filings,
    }
    (MARKDOWN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {MARKDOWN / 'manifest.json'} with {len(filings)} filings")


if __name__ == "__main__":
    main()
