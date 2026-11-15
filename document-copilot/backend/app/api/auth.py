from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me")
async def me(
    request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]
) -> dict[str, str]:
    """Return the signed-in analyst, creating their profile row on first sign-in."""
    await (
        request.app.state.supabase_admin.table("users")
        .upsert({"id": str(user.id), "email": user.email}, on_conflict="id")
        .execute()
    )
    return {"id": str(user.id), "email": user.email}
