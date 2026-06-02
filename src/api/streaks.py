from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from supabase import Client

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client
from src.types.streak import StreakIncrementResponse, StreakGetResponse

router = APIRouter()


def execute_increment_logic(sb: Client, user_id: str) -> dict:
    """Core synchronous streak processing logic executed inside an isolated thread

    to ensure database transitions never block the async event loop.
    """
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    response = sb.table("streaks").select("*").eq("user_id", user_id).execute()

    if not response.data:
        new_streak = {
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_active": today.isoformat(),
        }
        sb.table("streaks").insert(new_streak).execute()
        return {"current_streak": 1, "longest_streak": 1, "milestone": None}

    record = response.data[0]
    current_streak = record.get("current_streak", 0)
    longest_streak = record.get("longest_streak", 0)
    last_active_str = record.get("last_active")

    last_active = (
        datetime.fromisoformat(last_active_str).date() if last_active_str else None
    )

    if last_active == today:
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "milestone": None,
        }
    elif last_active == yesterday:
        current_streak += 1
    else:
        current_streak = 1

    if current_streak > longest_streak:
        longest_streak = current_streak

    milestone: Optional[int] = (
        current_streak if current_streak in [3, 7, 14, 30] else None
    )

    sb.table("streaks").update(
        {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_active": today.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", user_id).execute()

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "milestone": milestone,
    }


async def increment_user_streak(sb: Client, user_id: str) -> dict:
    """Exported helper function for external modules (like src/api/daily_focus.py)

    to safely increment streaks non-blockingly.
    """
    return await asyncio.to_thread(execute_increment_logic, sb, user_id)


@router.post("/increment", response_model=StreakIncrementResponse)
async def increment_streak(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
):
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)

    result = await increment_user_streak(sb, user_id)
    return StreakIncrementResponse(**result)


@router.get("/{user_id}", response_model=StreakGetResponse)
async def get_user_streak(
    user_id: str,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
):
    if str(current_user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user's streak data.",
        )

    sb = get_supabase_user_client(token)

    # CORRECTION: Wrapped in a lambda to cleanly execute the synchronous query block inside the worker thread
    response = await asyncio.to_thread(
        lambda: (
            sb.table("streaks")
            .select("current_streak", "longest_streak", "last_active")
            .eq("user_id", user_id)
            .execute()
        )
    )

    if not response.data:
        return StreakGetResponse(current_streak=0, longest_streak=0)

    record = response.data[0]
    db_current_streak = record.get("current_streak", 0)
    longest_streak = record.get("longest_streak", 0)
    last_active_str = record.get("last_active")

    live_current_streak = db_current_streak
    if last_active_str:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        last_active = datetime.fromisoformat(last_active_str).date()

        if last_active != today and last_active != yesterday:
            live_current_streak = 0

    return StreakGetResponse(
        current_streak=live_current_streak,
        longest_streak=longest_streak,
    )
