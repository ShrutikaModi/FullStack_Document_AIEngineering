from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.users import ensure_profile

router = APIRouter()


@router.get("/me")
async def me(
    request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]
) -> dict[str, str]:
    """Return the signed-in analyst, creating their profile row on first sign-in."""
    await ensure_profile(request.app.state.supabase_admin, user)
    return {"id": str(user.id), "email": user.email}
