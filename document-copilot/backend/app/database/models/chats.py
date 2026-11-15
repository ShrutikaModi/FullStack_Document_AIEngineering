from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt, UUIDPrimaryKey


class ChatThread(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "chat_threads"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant')", name="role_valid"),
    )

    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str]
    content: Mapped[str]
    # AI SDK message JSON, so history reloads exactly as the UI rendered it.
    parts: Mapped[list[Any] | None] = mapped_column(JSONB)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class MessageCitation(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "message_citations"

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"), index=True
    )
    # The [1], [2] marker shown next to the claim in the answer.
    label: Mapped[int]
