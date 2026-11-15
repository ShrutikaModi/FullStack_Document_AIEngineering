from uuid import UUID

from sqlalchemy import Column, ForeignKey, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt

# Stub of Supabase's own `auth.users`, only so the foreign key below is known to
# SQLAlchemy. Supabase owns that table; alembic/env.py never creates or alters it.
auth_users = Table(
    "users", Base.metadata, Column("id", Uuid, primary_key=True), schema="auth"
)


class User(CreatedAt, Base):
    """One row per analyst. `id` is the Supabase login id, so it has no default."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(unique=True)
