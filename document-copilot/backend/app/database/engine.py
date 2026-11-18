from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

# Retrieval needs vector and full-text SQL, which the Supabase REST client can't run,
# so the backend also keeps a small direct connection pool to Postgres.
POOL_SIZE = 5


def create_db_engine() -> AsyncEngine:
    """Lazy: no connection is opened until the first query."""
    return create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1),
        pool_size=POOL_SIZE,
        max_overflow=0,
        pool_pre_ping=True,
    )
