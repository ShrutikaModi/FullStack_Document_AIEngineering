from supabase import AsyncClient

from app.auth.dependencies import CurrentUser


async def ensure_profile(admin: AsyncClient, user: CurrentUser) -> None:
    """Create the analyst's `users` row on first use. Chats link to it."""
    await (
        admin.table("users")
        .upsert({"id": str(user.id), "email": user.email}, on_conflict="id")
        .execute()
    )
