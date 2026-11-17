"""Chunk, embed and store the Markdown filings in Supabase.

Run from backend/:  uv run python -m ingest.load_filings [--limit N] [--dry-run] [--with-embeddings]

Reads  data/markdown/manifest.json (filing facts) and the Markdown files it lists.
Writes one source_documents row per filing and its document_chunks rows.
Safe to re-run: filings already in the database (same accession number) are skipped,
and each filing is saved in one transaction, so a failure never leaves half a filing.
Embeddings are left empty unless --with-embeddings is given (they need an OpenAI key).
--dry-run chunks everything and prints a summary without calling OpenAI or the database.
"""

import argparse
import json
from datetime import date
from pathlib import Path

from openai import OpenAI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentChunk, SourceDocument
from ingest.chunking import Chunk, chunk_markdown

MARKDOWN = Path(__file__).resolve().parents[2] / "data" / "markdown"
EMBED_BATCH = 96


def embed(client: OpenAI, texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            input=texts[start : start + EMBED_BATCH],
        )
        vectors.extend(item.embedding for item in response.data)
    return vectors


def build_document(filing: dict, markdown: str) -> SourceDocument:
    return SourceDocument(
        ticker=filing["ticker"],
        company=filing["company"],
        form_type=filing["form"],
        fiscal_year=filing["fiscal_year"],
        filing_date=date.fromisoformat(filing["filing_date"]),
        accession_number=filing["accession_number"],
        source_url=filing["source_url"],
        markdown=markdown,
    )


def build_chunks(
    document: SourceDocument, chunks: list[Chunk], vectors: list[list[float] | None]
) -> list[DocumentChunk]:
    metadata = {
        "ticker": document.ticker,
        "company": document.company,
        "form_type": document.form_type,
        "fiscal_year": document.fiscal_year,
        "accession_number": document.accession_number,
    }
    return [
        DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.index,
            page=chunk.page,
            section=chunk.section,
            content=chunk.content,
            token_count=chunk.token_count,
            embedding=vector,
            chunk_metadata=metadata,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="load at most N new filings")
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="also create embeddings via OpenAI",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="chunk only; no OpenAI, no database"
    )
    args = parser.parse_args()

    manifest = json.loads((MARKDOWN / "manifest.json").read_text())
    if args.dry_run:
        for filing in manifest["filings"][: args.limit]:
            markdown = (MARKDOWN / filing["markdown_path"]).read_text()
            chunks = chunk_markdown(markdown)
            pages = sum(c.page is not None for c in chunks)
            sections = sum(c.section is not None for c in chunks)
            print(
                f"{filing['ticker']} {filing['fiscal_year']}: {len(chunks)} chunks, "
                f"{pages} with a page, {sections} with a section"
            )
        return

    engine = create_engine(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    client = (
        OpenAI(api_key=settings.openai_api_key, max_retries=5)
        if args.with_embeddings
        else None
    )
    loaded = skipped = 0

    for filing in manifest["filings"]:
        if args.limit and loaded >= args.limit:
            break
        label = f"{filing['ticker']} {filing['fiscal_year']}"
        with Session(engine) as session:
            exists = session.scalar(
                select(SourceDocument.id).where(
                    SourceDocument.accession_number == filing["accession_number"]
                )
            )
            if exists:
                skipped += 1
                print(f"skip  {label} (already loaded)")
                continue

            markdown = (MARKDOWN / filing["markdown_path"]).read_text()
            chunks = chunk_markdown(markdown)
            vectors = (
                embed(client, [c.content for c in chunks])
                if client
                else [None] * len(chunks)
            )
            document = build_document(filing, markdown)
            session.add(document)
            session.flush()  # assigns document.id for the chunk rows
            session.add_all(build_chunks(document, chunks, vectors))
            session.commit()
            loaded += 1
            print(f"load  {label}: {len(chunks)} chunks")

    print(f"done: {loaded} loaded, {skipped} skipped")


if __name__ == "__main__":
    main()
