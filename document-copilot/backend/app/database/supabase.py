from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import settings

# Server-side clients never keep a session: each request carries its own token.
_SERVER_OPTIONS = {"auto_refresh_token": False, "persist_session": False}


async def create_admin_client() -> AsyncClient:
    """Service-role client. Bypasses row-level security, so it must only act for a
    user the backend has already verified, and never be exposed to the browser."""
    return await acreate_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key,
        AsyncClientOptions(**_SERVER_OPTIONS),
    )


async def create_user_client(access_token: str) -> AsyncClient:
    """Anon-key client that acts as the signed-in user, so row-level security applies."""
    return await acreate_client(
        str(settings.supabase_url),
        settings.supabase_anon_key,
        AsyncClientOptions(
            headers={"Authorization": f"Bearer {access_token}"}, **_SERVER_OPTIONS
        ),
    )
