"""Create embeddings for every chunk that doesn't have one yet.

Run from backend/:  uv run python -m ingest.embed_chunks [--limit N]

Safe to re-run: only chunks with an empty embedding are processed, and each batch is
saved as soon as it is done, so an interruption loses at most one batch.
"""

import argparse
import time

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentChunk
from app.openai_client import create_openai_client

BATCH = 64


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, help="embed at most N chunks (for testing)"
    )
    args = parser.parse_args()

    engine = create_engine(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    client = create_openai_client()
    started = time.perf_counter()
    done = 0

    with Session(engine) as session:
        pending = session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.embedding.is_(None))
        )
        total = min(pending, args.limit) if args.limit else pending
        print(f"{pending} chunks need embeddings; embedding {total}")

        while done < total:
            size = min(BATCH, total - done)
            rows = session.execute(
                select(DocumentChunk.id, DocumentChunk.content)
                .where(DocumentChunk.embedding.is_(None))
                .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
                .limit(size)
            ).all()
            if not rows:
                break
            response = client.embeddings.create(
                model=settings.openai_embedding_model,
                dimensions=settings.openai_embedding_dimensions,
                input=[content for _, content in rows],
            )
            session.execute(
                update(DocumentChunk),
                [
                    {"id": row_id, "embedding": item.embedding}
                    for (row_id, _), item in zip(rows, response.data, strict=True)
                ],
            )
            session.commit()
            done += len(rows)
            if done % (BATCH * 10) < BATCH or done == total:
                print(f"{done}/{total} embedded ({time.perf_counter() - started:.0f}s)")

    print(f"done: {done} chunks embedded")


if __name__ == "__main__":
    main()
