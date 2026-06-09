from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.openai_service import _chat
from src.lib.supabase import get_supabase_user_client
from src.types.progress import (
    GeminiProgressInsight,
    ProgressResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Progress"])


def execute_fallback_logic(
    sessions_done: int, avg_lift: float
) -> GeminiProgressInsight:
    """Generates a contextual fallback insight based on core anxiety lift performance."""
    logger.warning("Executing local fallback logic for progress insight.")

    if sessions_done == 0:
        return GeminiProgressInsight(
            key_insight="Welcome to MindGym! Complete your first session today to kick off your progress insights."
        )

    if avg_lift > 0:
        return GeminiProgressInsight(
            key_insight=f"Great job! You're reducing anxiety by an average of {avg_lift} points per session. Keep it up."
        )

    return GeminiProgressInsight(
        key_insight="You're building consistency. Dedicating a few minutes to mindful breathing today can help turn things around."
    )


@router.get(
    "/progress",
    response_model=ProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated user session metrics, trends, and insights",
)
async def get_progress(
    current_user_id: Annotated[UUID, Depends(CurrentUserId)],
    token: Annotated[str, Depends(CurrentUserToken)],
    period: Literal["week", "month", "all"] = Query("week"),
):
    sb = get_supabase_user_client(token)
    user_uuid_str = str(current_user_id)
    now = datetime.now(UTC)

    # STEP 1: Fetch data from Supabase
    try:
        streak_res = await asyncio.to_thread(
            sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_uuid_str)
            .maybe_single()
            .execute
        )
        day_streak = (
            streak_res.data.get("current_streak", 0) if streak_res.data else 0
        )

        start_date = None
        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)

        query = (
            sb.table("ai_sessions")
            .select("anxiety_level_before", "anxiety_level_after", "completed_at")
            .eq("user_id", user_uuid_str)
            .not_.is_("completed_at", "null")
        )
        if start_date:
            query = query.gte("completed_at", start_date.isoformat())

        sessions_res = await asyncio.to_thread(
            query.order("completed_at", ascending=True).execute
        )
        sessions = sessions_res.data or []

    except Exception as db_err:
        logger.error(f"Failed to fetch user progress context: {str(db_err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up user progress history.",
        )

    if not sessions:
        return ProgressResponse(
            sessions_done=0,
            day_streak=day_streak,
            avg_lift_per_session=0.0,
            key_insight="",
        )

    # STEP 2: Aggregate Verified Schema Metrics
    sessions_done = len(sessions)
    total_lift = 0.0

    for s in sessions:
        pre_score = s.get("anxiety_level_before") or 0.0
        post_score = s.get("anxiety_level_after") or 0.0
        total_lift += float(pre_score) - float(post_score)

    avg_lift_per_session = round(total_lift / sessions_done, 1)

    # STEP 3: Build Lean Prompt focused on actual data
    prompt = f"""
    You are an expert, supportive AI MindGym coach analyzing user progress.
    Review the metrics below and output an actionable coaching summary sentence.

    --- USER PROGRESS METRICS ---
    Total complete sessions: {sessions_done}
    Average anxiety reduction lift per session: {avg_lift_per_session} points
    Current user day streak: {day_streak} days

    --- STRATEGIC CONSTRAINTS ---
    1. Provide a concise, supportive translation of their anxiety reduction metrics or streak milestones.
    2. Suggest a minor actionable target goal for their mental fitness routine.
    3. The coaching statement inside the key_insight property must be under 20 words total.
    4. You MUST output raw JSON matching this structure exactly. No markdown blocks.

    {{
       "key_insight": "..."
    }}
    """

    try:
        raw_text = await asyncio.wait_for(
            asyncio.to_thread(
                _chat,
                system="You are a precise JSON coaching metrics assistant.",
                user=prompt,
            ),
            timeout=4.0,
        )

        if raw_text is None:
            raise ValueError("OpenAI pipeline failed to return response string.")

        parsed_json = json.loads(raw_text.strip())
        validated_insight = GeminiProgressInsight(**parsed_json)
    except (asyncio.TimeoutError, Exception) as err:
        logger.error(f"OpenAI progress insight calculation failed: {repr(err)}")
        validated_insight = execute_fallback_logic(sessions_done, avg_lift_per_session)

    if not validated_insight or not validated_insight.key_insight:
        validated_insight = execute_fallback_logic(sessions_done, avg_lift_per_session)

    clean_insight_str = " ".join(validated_insight.key_insight.split()[:20])

    # STEP 4: Package and Return Lean Data
    return ProgressResponse(
        sessions_done=sessions_done,
        day_streak=day_streak,
        avg_lift_per_session=avg_lift_per_session,
        key_insight=clean_insight_str,
    )
