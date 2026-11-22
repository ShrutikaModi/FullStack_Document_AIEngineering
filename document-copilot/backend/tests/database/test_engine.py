import pytest

from app.database.engine import POOL_SIZE, create_db_engine, migration_url
from app.openai_client import create_async_openai_client, create_openai_client


def test_engine_uses_the_async_psycopg_driver_and_a_small_pool():
    engine = create_db_engine()
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.pool.size() == POOL_SIZE


def test_engine_opens_no_connection_until_used():
    engine = create_db_engine()
    assert engine.pool.checkedout() == 0


@pytest.mark.parametrize("factory", [create_openai_client, create_async_openai_client])
def test_openai_clients_use_the_configured_key(factory):
    from app.config import settings

    assert factory().api_key == settings.openai_api_key


DIRECT = "postgresql://postgres:pw@db.abc.supabase.co:5432/postgres"
SESSION_POOLER = (
    "postgresql://postgres.abc:pw@aws-0-eu.pooler.supabase.com:5432/postgres"
)
TRANSACTION_POOLER = (
    "postgresql://postgres.abc:pw@aws-0-eu.pooler.supabase.com:6543/postgres"
)


@pytest.mark.parametrize("url", [DIRECT, SESSION_POOLER])
def test_migrations_can_use_a_session_connection(url):
    assert migration_url(url).startswith("postgresql+psycopg://")


def test_migrations_refuse_the_transaction_pooler():
    with pytest.raises(ValueError, match="transaction pooler"):
        migration_url(TRANSACTION_POOLER)
