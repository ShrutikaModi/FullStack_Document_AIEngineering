from datetime import date
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database.models.base import Base, CreatedAt, UUIDPrimaryKey


class SourceDocument(UUIDPrimaryKey, CreatedAt, Base):
    """One SEC filing, stored as normalized Markdown so it can be re-chunked."""

    __tablename__ = "source_documents"

    ticker: Mapped[str]
    company: Mapped[str]
    form_type: Mapped[str]
    fiscal_year: Mapped[int]
    filing_date: Mapped[date]
    accession_number: Mapped[str] = mapped_column(unique=True)
    source_url: Mapped[str]
    markdown: Mapped[str]


class DocumentChunk(UUIDPrimaryKey, CreatedAt, Base):
    """A retrieval-ready passage. HNSW and GIN indexes are added in the migration."""

    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int]
    page: Mapped[int | None]
    section: Mapped[str | None]
    content: Mapped[str]
    token_count: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.openai_embedding_dimensions)
    )
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True)
    )
    # `metadata` is reserved on declarative classes, so the attribute is renamed.
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
