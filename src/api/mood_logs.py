from __future__ import annotations

import logging
import asyncio
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
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    period: str = Query("week", pattern="^(week|month|all)$"),
):
    try:
        sb = get_supabase_user_client(token)
        today_utc = datetime.now(timezone.utc).date()

        # Calculate cutoffs for database query optimization
        cutoff_date = None
        if period == "week":
            cutoff_date = today_utc - timedelta(days=7)
        elif period == "month":
            cutoff_date = today_utc - timedelta(days=30)

        # Always fetch at least the last 7 days of logs to populate the timeline
        timeline_cutoff = today_utc - timedelta(days=7)
        db_cutoff = cutoff_date if cutoff_date else timeline_cutoff

        if period == "all":
            db_cutoff = None

        # Defined a valid inner function to handle the multi-step query logic safely
        def fetch_logs():
            query = (
                sb.table("mood_logs")
                .select("score, created_at")
                .eq("user_id", str(current_user_id))
            )
            if db_cutoff:
                query = query.gte("created_at", db_cutoff.isoformat())
            return query.order("created_at", descending=True).execute()

        # Delegate the query safely to the thread pool
        result = await asyncio.to_thread(fetch_logs)
        all_logs = result.data or []

        # 1. Compute summary metrics using optimized in-memory partitions
        filtered_logs = all_logs
        if period != "all" and cutoff_date:
            filtered_logs = [
                log
                for log in all_logs
                if datetime.fromisoformat(
                    log["created_at"].replace("Z", "+00:00")
                ).date()
                >= cutoff_date
            ]

        total_logs = len(filtered_logs)
        avg_score = None
        if total_logs > 0:
            avg_score = round(
                sum(log["score"] for log in filtered_logs) / total_logs, 1
            )

        # 2. Map tracking points out for structural 7-day sparkline grids
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
