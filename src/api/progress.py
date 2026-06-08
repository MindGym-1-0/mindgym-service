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
    ConfidenceDataPoint,
    EmotionalStates,
    GeminiProgressInsight,
    ProgressResponse,
)

logger = logging.getLogger(__name__)
# Fixed: Router prefix removed to avoid /api/api/progress path resolution errors
router = APIRouter(tags=["Progress"])


def execute_fallback_logic(
    lowest_dimension: str, final_states: dict[str, float]
) -> GeminiProgressInsight:
    """Generates a contextual fallback insight if the AI provider fails."""
    logger.warning("Executing local fallback logic for progress insight.")
    dim_capitalized = lowest_dimension.capitalize()

    if final_states.get(lowest_dimension, 0) == 0:
        return GeminiProgressInsight(
            key_insight=f"No sessions recorded for {lowest_dimension} yet. "
            f"Try dedicating your next session to it."
        )

    return GeminiProgressInsight(
        key_insight=f"{dim_capitalized} is your current focus area. "
        f"Consistency this week will help push it higher."
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

    # STEP 1: Fetch data from Supabase using thread executors
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
            .select("*")
            .eq("user_id", user_uuid_str)
            .eq("completed", True)
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
            avg_confidence=0.0,
            sessions_done=0,
            day_streak=day_streak,
            avg_lift_per_session=0.0,
            confidence_over_time=[],
            emotional_states=EmotionalStates(),
            key_insight="",
        )

    # STEP 2: Aggregate Metrics & Processing Loops
    sessions_done = len(sessions)
    total_lift = 0.0

    state_metrics = {
        "confidence": {"sum": 0.0, "count": 0},
        "clarity": {"sum": 0.0, "count": 0},
        "calmness": {"sum": 0.0, "count": 0},
        "focus": {"sum": 0.0, "count": 0},
    }

    for s in sessions:
        post_score = s.get("post_score") or s.get("anxiety_level_after") or 0.0
        pre_score = s.get("pre_score") or s.get("anxiety_level_before") or 0.0
        total_lift += float(post_score) - float(pre_score)

        for dimension in state_metrics.keys():
            val = s.get(dimension) or s.get(f"post_{dimension}")
            if val is not None:
                state_metrics[dimension]["sum"] += float(val)
                state_metrics[dimension]["count"] += 1

    avg_lift_per_session = round(total_lift / sessions_done, 1)

    final_states = {}
    for dim, data in state_metrics.items():
        final_states[dim] = (
            round(data["sum"] / data["count"], 1) if data["count"] > 0 else 0.0
        )

    avg_confidence = final_states["confidence"]

    # STEP 3: Compile Time Series Maps (confidence_over_time)
    confidence_over_time: list[ConfidenceDataPoint] = []

    if period == "week":
        days_map: dict[str, list[float]] = {}
        for s in sessions:
            dt = datetime.fromisoformat(
                s["completed_at"].replace("Z", "+00:00")
            )
            day_label = dt.strftime("%a")
            days_map.setdefault(day_label, []).append(
                s.get("confidence") or s.get("post_confidence") or 0.0
            )

        current_day_label = now.strftime("%a")
        for day_label, vals in days_map.items():
            label = "Today" if day_label == current_day_label else day_label
            confidence_over_time.append(
                ConfidenceDataPoint(
                    day=label, value=round(sum(vals) / len(vals), 1)
                )
            )

    elif period == "month":
        weeks_map: dict[str, list[float]] = {}
        for s in sessions:
            dt = datetime.fromisoformat(
                s["completed_at"].replace("Z", "+00:00")
            )
            week_label = f"Wk {dt.isocalendar()[1]}"
            weeks_map.setdefault(week_label, []).append(
                s.get("confidence") or s.get("post_confidence") or 0.0
            )

        for week_label, vals in weeks_map.items():
            confidence_over_time.append(
                ConfidenceDataPoint(
                    day=week_label, value=round(sum(vals) / len(vals), 1)
                )
            )

    else:
        months_map: dict[str, list[float]] = {}
        for s in sessions:
            dt = datetime.fromisoformat(
                s["completed_at"].replace("Z", "+00:00")
            )
            month_label = dt.strftime("%b")
            months_map.setdefault(month_label, []).append(
                s.get("confidence") or s.get("post_confidence") or 0.0
            )

        for month_label, vals in months_map.items():
            confidence_over_time.append(
                ConfidenceDataPoint(
                    day=month_label, value=round(sum(vals) / len(vals), 1)
                )
            )

    # STEP 4: Build Prompt & Execute OpenAI chat sequence
    lowest_dimension = min(final_states, key=final_states.get)

    prompt = f"""
    You are an expert, supportive AI MindGym coach analyzing user progress.
    Review the metrics below and output an actionable coaching summary sentence.

    --- USER PROGRESS METRICS ---
    Averages for current timeframe: {final_states}
    Lowest performing dimension: {lowest_dimension}
    Total complete sessions: {sessions_done}
    Current user day streak: {day_streak} days

    --- STRATEGIC CONSTRAINTS ---
    1. Your answer must focus explicitly on improving: {lowest_dimension}.
    2. Suggest a real, minor actionable next target goal.
    3. The text constraint is strict: it must be under 20 words total.
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
        validated_insight = execute_fallback_logic(
            lowest_dimension, final_states
        )

    if not validated_insight or not validated_insight.key_insight:
        validated_insight = execute_fallback_logic(
            lowest_dimension, final_states
        )

    clean_insight_str = " ".join(validated_insight.key_insight.split()[:20])

    # STEP 5: Package and Return Data
    return ProgressResponse(
        avg_confidence=avg_confidence,
        sessions_done=sessions_done,
        day_streak=day_streak,
        avg_lift_per_session=avg_lift_per_session,
        confidence_over_time=confidence_over_time,
        emotional_states=EmotionalStates(**final_states),
        key_insight=clean_insight_str,
    )
