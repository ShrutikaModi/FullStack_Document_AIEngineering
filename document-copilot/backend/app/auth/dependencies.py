from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthApiError

# auto_error=False so a missing header becomes our 401, not FastAPI's default 403.
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    # Whether the address is confirmed, so nobody gains access by signing up with someone
    # else's address.
    email_confirmed: bool
    access_token: str


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> CurrentUser:
    """Verify the caller's Supabase token before any chat or retrieval work."""
    if credentials is None:
        raise unauthorized("Missing bearer token")

    token = credentials.credentials
    try:
        response = await request.app.state.supabase_admin.auth.get_user(token)
    except AuthApiError:
        raise unauthorized("Invalid or expired token") from None
    if response is None or response.user is None or not response.user.email:
        raise unauthorized("Invalid or expired token")

    return CurrentUser(
        id=UUID(response.user.id),
        email=response.user.email,
        email_confirmed=response.user.email_confirmed_at is not None,
        access_token=token,
    )
