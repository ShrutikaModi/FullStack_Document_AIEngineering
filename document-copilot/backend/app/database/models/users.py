from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAt


class User(CreatedAt, Base):
    """One row per analyst.

    `id` is the Supabase `auth.users.id`, so it has no default. The foreign key
    to `auth.users` lives in the migration: that schema isn't in our metadata.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
