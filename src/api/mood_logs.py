# src/api/mood_logs.py

from __future__ import annotations
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status

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
    """Saves a user's mood log score (1-10) and optional note to the database."""
    try:
        sb = get_supabase_user_client(token)
        result = (
            sb.table("mood_logs")
            .insert(
                {
                    "user_id": str(payload.user_id),
                    "score": payload.score,
                    "note": payload.note,
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist mood log record.",
            )

        return result.data[0]
    except Exception as e:
        logger.error(f"Error creating mood log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database communication error: {str(e)}",
        )


@router.get(
    "/summary",
    response_model=MoodLogSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get mood log historical summary metrics",
)
async def get_mood_summary(
    user_id: UUID, current_user_id: CurrentUserId, token: CurrentUserToken
):
    """
    Calculates avg_score, total_logs, and returns a 7-day timeline array
    starting from Today descending.
    """
    try:
        sb = get_supabase_user_client(token)
        result = (
            sb.table("mood_logs")
            .select("score, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", descending=True)
            .execute()
        )

        logs = result.data or []
        total_logs = len(logs)

        avg_score = None
        if total_logs > 0:
            avg_score = round(sum(log["score"] for log in logs) / total_logs, 1)

        daily_scores_map: Dict[str, int] = {}
        for log in reversed(logs):
            log_date_str = log["created_at"].split("T")[0]
            daily_scores_map[log_date_str] = log["score"]

        last_7_days_list = []
        today = date.today()

        for i in range(7):
            target_date = today - timedelta(days=i)
            target_date_str = target_date.strftime("%Y-%m-%d")
            day_score = daily_scores_map.get(target_date_str, None)

            last_7_days_list.append(
                DailyMoodHistoryItem(date=target_date_str, score=day_score)
            )

        return MoodLogSummaryResponse(
            avg_score=avg_score, total_logs=total_logs, last_7_days=last_7_days_list
        )

    except Exception as e:
        logger.error(f"Error compiling mood log summary details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal aggregation calculation error: {str(e)}",
        )
