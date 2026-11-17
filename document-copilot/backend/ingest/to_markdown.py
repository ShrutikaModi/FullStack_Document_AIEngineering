"""Convert the downloaded SEC filings (HTML) to Markdown with Docling.

Run from backend/:  uv run python -m ingest.to_markdown [--limit N] [--force] [--tickers JPM,GOOGL]

Reads  data/downloads/<year>/<file>.htm
Writes data/markdown/<year>/<file>.md   (skips files already converted unless --force)
"""

import argparse
import tempfile
import time
from pathlib import Path

from docling.document_converter import DocumentConverter

from ingest.page_markers import add_page_markers

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOWNLOADS = DATA_DIR / "downloads"
MARKDOWN = DATA_DIR / "markdown"


def convert(converter: DocumentConverter, source: Path) -> str:
    """HTML -> Markdown, with [[PAGE n]] lines added where the filing marks page breaks."""
    html, markers = add_page_markers(
        source.read_text(encoding="utf-8", errors="ignore")
    )
    if not markers:
        return converter.convert(source).document.export_to_markdown()
    with tempfile.TemporaryDirectory() as folder:
        marked = Path(folder) / source.name
        marked.write_text(html, encoding="utf-8")
        return converter.convert(marked).document.export_to_markdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, help="convert at most N files (for testing)"
    )
    parser.add_argument(
        "--force", action="store_true", help="redo files already converted"
    )
    parser.add_argument(
        "--tickers", help="only these tickers, comma separated, e.g. JPM,GOOGL"
    )
    args = parser.parse_args()

    sources = sorted(p for p in DOWNLOADS.glob("*/*") if p.suffix in {".htm", ".html"})
    if args.tickers:
        wanted = {t.strip().lower() for t in args.tickers.split(",")}
        sources = [p for p in sources if p.name.split("_")[0] in wanted]
    converter = DocumentConverter()
    done = failed = skipped = 0

    for source in sources:
        target = MARKDOWN / source.parent.name / f"{source.stem}.md"
        if target.exists() and not args.force:
            skipped += 1
            continue
        if args.limit is not None and done + failed >= args.limit:
            break

        started = time.perf_counter()
        try:
            markdown = convert(converter, source)
        except Exception as error:  # noqa: BLE001  one bad filing shouldn't stop the batch
            failed += 1
            print(f"FAILED  {source.name}: {error}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        done += 1
        seconds = time.perf_counter() - started
        print(
            f"ok      {source.name} -> {len(markdown) / 1000:,.0f} KB markdown in {seconds:.0f}s"
        )

    print(
        f"\nconverted {done}, failed {failed}, already done {skipped}, total {len(sources)}"
    )


if __name__ == "__main__":
    main()
