from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import AsyncClient

Row = dict[str, Any]


async def list_threads(admin: AsyncClient, user_id: UUID) -> list[Row]:
    response = await (
        admin.table("chat_threads")
        .select("id,title,created_at,updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def create_thread(admin: AsyncClient, user_id: UUID) -> Row:
    response = await (
        admin.table("chat_threads").insert({"user_id": str(user_id)}).execute()
    )
    return response.data[0]


async def get_owned_thread(admin: AsyncClient, thread_id: UUID, user_id: UUID) -> Row:
    """Load a thread, or fail: 404 if it doesn't exist, 403 if it is someone else's.

    Every route that touches a thread goes through here, so ownership is checked in
    one place. The admin client bypasses row-level security, so this check is what
    keeps analysts out of each other's chats.
    """
    response = await (
        admin.table("chat_threads")
        .select("*")
        .eq("id", str(thread_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(404, "Thread not found")
    thread = response.data[0]
    if thread["user_id"] != str(user_id):
        raise HTTPException(403, "This thread belongs to another user")
    return thread


async def list_messages(admin: AsyncClient, thread_id: UUID) -> list[Row]:
    response = await (
        admin.table("chat_messages")
        .select("id,role,parts,created_at")
        .eq("thread_id", str(thread_id))
        .order("created_at")
        .execute()
    )
    return response.data


async def recent_messages(admin: AsyncClient, thread_id: UUID, count: int) -> list[Row]:
    """The last `count` messages of a thread, oldest first.

    Only the newest few are read, so a long conversation doesn't get slower or costlier.
    """
    response = await (
        admin.table("chat_messages")
        .select("id,role,parts,created_at")
        .eq("thread_id", str(thread_id))
        .order("created_at", desc=True)
        .limit(count)
        .execute()
    )
    return list(
        reversed(response.data)
    )  # fetched newest first, handed back oldest first


async def save_turn(
    admin: AsyncClient,
    thread: Row,
    user_message: Row,
    assistant_message: Row,
    title: str,
) -> None:
    """Store both messages of a finished turn in one insert, then touch the thread.

    The caller sets `created_at` on each message so their order is unambiguous.
    `title` is applied only if the thread has none yet, so it never changes later.
    """
    await (
        admin.table("chat_messages").insert([user_message, assistant_message]).execute()
    )
    changes: Row = {"updated_at": datetime.now(UTC).isoformat()}
    if not thread["title"]:
        changes["title"] = title
    await admin.table("chat_threads").update(changes).eq("id", thread["id"]).execute()
