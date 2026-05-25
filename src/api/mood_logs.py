# src/api/mood_logs.py

from __future__ import annotations
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime, timedelta, timezone
from typing import Dict  # Fix: Add explicit typing import for Flake8

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
    """Saves an authenticated user's mood log score (1-10) and optional note to the database.

    Enforces the authenticated session identity to block multi-tenant ID spoofing.
    """
    try:
        sb = get_supabase_user_client(token)
        result = (
            sb.table("mood_logs")
            .insert(
                {
                    "user_id": str(
                        current_user_id
                    ),  # Fix 2: Overwrite payload context with verified caller ID
                    "score": payload.score,
                    "note": payload.note,
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again.",
            )

        return result.data[0]
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating mood log: {str(e)}")  # Keep full tracing context internally
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",  # Fix 3: Sanitize leaky message variants
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
    ),  # Fix: Updated deprecated 'regex' to 'pattern'
):
    """Calculates average mood scores according to a chosen historic interval window, and returns a

    standardized 7-day timeline matrix using strict UTC temporal alignments.
    """
    # Fix 1: Explicit cross-tenant guard rule. Deny cross-reads across user profiles.
    if str(user_id) != str(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to requested profile metrics is denied.",
        )

    try:
        sb = get_supabase_user_client(token)
        result = (
            sb.table("mood_logs")
            .select("score, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", descending=True)  # Raw database sequence output is modern-first
            .execute()
        )

        all_logs = result.data or []

        # Fix 6: Ground date assessments uniformly in UTC to resolve server local shifting anomalies
        today_utc = datetime.now(timezone.utc).date()

        # ----------------=======================================
        # TIME PERIOD HORIZON FILTERING (Figma Metric Overlays)
        # -------------------------------------------------------
        filtered_logs = []
        if period == "week":
            cutoff = today_utc - timedelta(days=7)
            filtered_logs = [
                log
                for log in all_logs
                if datetime.fromisoformat(log["created_at"].replace("Z", "+00:00")).date()
                >= cutoff
            ]  # Fix: Replaced ambiguous 'l' with 'log'
        elif period == "month":
            cutoff = today_utc - timedelta(days=30)
            filtered_logs = [
                log
                for log in all_logs
                if datetime.fromisoformat(log["created_at"].replace("Z", "+00:00")).date()
                >= cutoff
            ]  # Fix: Replaced ambiguous 'l' with 'log'
        else:
            filtered_logs = all_logs

        total_logs = len(filtered_logs)
        avg_score = None
        if total_logs > 0:
            avg_score = round(sum(log["score"] for log in filtered_logs) / total_logs, 1)

        # ----------------=======================================
        # HISTORIC CHRONOLOGY GRID PROCESSING (7-Day Metric View)
        # -------------------------------------------------------
        daily_scores_map: Dict[str, int] = {}
        # Fix 4: Stripped reversed(). Since it's sorted DESC, parsing naturally captures the latest record per day first.
        for log in all_logs:
            log_date_str = log["created_at"].split("T")[0]
            if log_date_str not in daily_scores_map:
                daily_scores_map[log_date_str] = log["score"]

        last_7_days_list = []
        for i in range(7):
            target_date = today_utc - timedelta(days=i)
            target_date_str = target_date.strftime("%Y-%m-%d")
            day_score = daily_scores_map.get(target_date_str, None)

            last_7_days_list.append(DailyMoodHistoryItem(date=target_date_str, score=day_score))

        return MoodLogSummaryResponse(
            avg_score=avg_score, total_logs=total_logs, last_7_days=last_7_days_list
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error compiling mood log summary details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )
