import pytest

from app.config import settings
from app.database.supabase import create_admin_client, create_user_client

pytestmark = pytest.mark.anyio


async def test_admin_client_uses_service_role_key():
    client = await create_admin_client()
    assert client.supabase_key == settings.supabase_service_role_key


async def test_user_client_uses_anon_key_and_caller_token():
    client = await create_user_client("user-jwt")
    assert client.supabase_key == settings.supabase_anon_key
    assert client.options.headers["Authorization"] == "Bearer user-jwt"
