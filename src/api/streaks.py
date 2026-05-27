from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client
from src.types.streak import StreakIncrementResponse, StreakGetResponse

router = APIRouter()


@router.post("/increment", response_model=StreakIncrementResponse)
async def increment_streak(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    sb: Client = Depends(get_supabase_user_client),
):
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    response = (
        sb.table("streaks").select("*").eq("user_id", str(current_user_id)).execute()
    )

    if not response.data:
        new_streak = {
            "user_id": str(current_user_id),
            "current_streak": 1,
            "longest_streak": 1,
            "last_active": today.isoformat(),
        }
        sb.table("streaks").insert(new_streak).execute()
        return StreakIncrementResponse(
            current_streak=1, longest_streak=1, milestone=None
        )

    record = response.data[0]
    # Use .get() to avoid KeyError
    current_streak = record.get("current_streak", 0)
    longest_streak = record.get("longest_streak", 0)

    last_active_str = record.get("last_active")
    last_active = (
        datetime.fromisoformat(last_active_str).date() if last_active_str else None
    )

    if last_active == today:
        return StreakIncrementResponse(
            current_streak=current_streak, longest_streak=longest_streak, milestone=None
        )
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
    ).eq("user_id", str(current_user_id)).execute()

    return StreakIncrementResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        milestone=milestone,
    )


@router.get("/{user_id}", response_model=StreakGetResponse)
async def get_user_streak(
    user_id: str,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    sb: Client = Depends(get_supabase_user_client),
):
    if str(current_user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user's streak data.",
        )

    response = (
        sb.table("streaks")
        .select("current_streak", "longest_streak", "last_active")
        .eq("user_id", user_id)
        .execute()
    )

    if not response.data:
        return StreakGetResponse(current_streak=0, longest_streak=0)

    record = response.data[0]
    # Use .get() to avoid KeyError
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
