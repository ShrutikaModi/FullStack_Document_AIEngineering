from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

# Retrieval needs vector and full-text SQL, which the Supabase REST client can't run,
# so the backend also keeps a small connection pool to Postgres.
POOL_SIZE = 5

# Supabase's transaction pooler: hands a connection out per transaction, not per session.
TRANSACTION_POOLER = "pooler.supabase.com:6543"


def create_db_engine() -> AsyncEngine:
    """Lazy: no connection is opened until the first query."""
    return create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1),
        pool_size=POOL_SIZE,
        max_overflow=0,
        pool_pre_ping=True,
        # No prepared statements: the transaction pooler (used when hosted) does not support
        # them, because the next query may land on a different server connection. Costs
        # nothing noticeable on a direct connection.
        connect_args={"prepare_threshold": None},
    )


def migration_url(database_url: str) -> str:
    """The URL Alembic uses. Migrations create extensions and indexes, which need a real
    session, so the transaction pooler is refused (the direct or session URL both work)."""
    if TRANSACTION_POOLER in database_url:
        raise ValueError(
            "Migrations need the direct connection (or the session pooler, port 5432), "
            "not the transaction pooler (port 6543). Set DATABASE_URL to it when migrating."
        )
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
