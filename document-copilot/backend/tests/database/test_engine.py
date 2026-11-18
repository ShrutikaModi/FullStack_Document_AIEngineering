import pytest

from app.database.engine import POOL_SIZE, create_db_engine
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
