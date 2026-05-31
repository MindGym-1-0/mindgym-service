from __future__ import annotations
import logging
import asyncio  # Added for thread pool delegation
from uuid import UUID
from typing import Dict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status, Query

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client
from src.types.mood_log import (
    MoodLogCreate,
    MoodLogResponse,
    MoodLogSummaryResponse,
    DailyMoodHistoryItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=MoodLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new mood log",
)
async def create_mood_log(
    payload: MoodLogCreate, current_user_id: CurrentUserId, token: CurrentUserToken
):
    try:
        sb = get_supabase_user_client(token)

        # Wrapped synchronous Supabase call in asyncio.to_thread
        result = await asyncio.to_thread(
            lambda: (
                sb.table("mood_logs")
                .insert(
                    {
                        "user_id": str(current_user_id),
                        "score": payload.score,
                        "note": payload.note,
                    }
                )
                .execute()
            )
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again.",
            )

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mood log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.get(
    "/summary",
    response_model=MoodLogSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get mood log historical summary metrics",
)
async def get_mood_summary(
    user_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    period: str = Query(
        "week", pattern="^(week|month|all)$"
    ),  # Cleaned up deprecated regex arg
):
    if str(user_id) != str(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to requested profile metrics is denied.",
        )

    try:
        sb = get_supabase_user_client(token)

        # Wrapped synchronous Supabase query loop in asyncio.to_thread
        result = await asyncio.to_thread(
            lambda: (
                sb.table("mood_logs")
                .select("score, created_at")
                .eq("user_id", str(user_id))
                .order("created_at", descending=True)
                .execute()
            )
        )

        all_logs = result.data or []
        today_utc = datetime.now(timezone.utc).date()

        filtered_logs = []
        if period == "week":
            cutoff = today_utc - timedelta(days=7)
            filtered_logs = [
                log
                for log in all_logs
                if datetime.fromisoformat(
                    log["created_at"].replace("Z", "+00:00")
                ).date()
                >= cutoff
            ]
        elif period == "month":
            cutoff = today_utc - timedelta(days=30)
            filtered_logs = [
                log
                for log in all_logs
                if datetime.fromisoformat(
                    log["created_at"].replace("Z", "+00:00")
                ).date()
                >= cutoff
            ]
        else:
            filtered_logs = all_logs

        total_logs = len(filtered_logs)
        avg_score = None
        if total_logs > 0:
            avg_score = round(
                sum(log["score"] for log in filtered_logs) / total_logs, 1
            )

        daily_scores_map: Dict[str, int] = {}
        for log in all_logs:
            log_date_str = log["created_at"].split("T")[0]
            if log_date_str not in daily_scores_map:
                daily_scores_map[log_date_str] = log["score"]

        last_7_days_list = []
        for i in range(7):
            target_date = today_utc - timedelta(days=i)
            target_date_str = target_date.strftime("%Y-%m-%d")
            day_score = daily_scores_map.get(target_date_str, None)
            last_7_days_list.append(
                DailyMoodHistoryItem(date=target_date_str, score=day_score)
            )

        return MoodLogSummaryResponse(
            avg_score=avg_score, total_logs=total_logs, last_7_days=last_7_days_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compiling mood log summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )
