from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.openai_service import _chat
from src.lib.supabase import get_supabase_user_client
from src.types.progress import (
    ProgressInsight,
    ProgressResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/progress", tags=["Progress"])


def execute_fallback_logic(
    sessions_done: int, avg_lift: float
) -> ProgressInsight:
    """Generates a contextual fallback insight based on core anxiety lift performance."""
    logger.warning("Executing local fallback logic for progress insight.")

    if sessions_done == 0:
        return ProgressInsight(
            key_insight="Welcome to MindGym! Complete your first session today to kick off your progress insights."
        )

    if avg_lift < 0:  
        return ProgressInsight(
            key_insight=f"Great job! You're reducing anxiety by an average of {abs(avg_lift)} points per session. Keep it up."
        )

    return ProgressInsight(
        key_insight="You're building consistency. Dedicating a few minutes to mindful breathing today can help turn things around."
    )


@router.get(
    "",
    response_model=ProgressResponse,
    summary="Get aggregated user session metrics, trends, and insights",
)
async def get_progress(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    period: str = "week",
):
    sb = get_supabase_user_client(token)
    user_uuid_str = str(current_user_id)
    now = datetime.now(UTC)

    # --- STEP 1: Fetch Streak Data Safely ---
    day_streak = 0
    try:
        streak_res = await asyncio.to_thread(
            lambda: sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_uuid_str)
            .maybe_single()
            .execute()
        )
        if streak_res and streak_res.data:
            day_streak = streak_res.data.get("current_streak", 0)
    except Exception as streak_err:
        logger.warning(f"Failed to fetch streaks (defaulting to 0): {str(streak_err)}")
        day_streak = 0

    # --- STEP 2: Fetch Sessions Data Safely ---
    sessions = []
    try:
        start_date = None
        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)

        base_query = (
            sb.table("ai_sessions")
            .select("anxiety_level_before, anxiety_level_after, completed_at")
            .eq("user_id", user_uuid_str)
            .not_.is_("completed_at", "null")
        )
        if start_date:
            base_query = base_query.gte("completed_at", start_date.isoformat())

        final_query = base_query.order("completed_at", desc=False)
        sessions_res = await asyncio.to_thread(lambda: final_query.execute())
        if sessions_res and sessions_res.data:
            sessions = sessions_res.data
    except Exception as db_err:
        logger.error(f"Failed to fetch user progress context: {str(db_err)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to look up user progress history.",
        )

    # --- STEP 3: Return Baseline If No Data Exists ---
    if not sessions:
        return ProgressResponse(
            sessions_done=0,
            day_streak=day_streak,
            avg_lift_per_session=0.0,
            key_insight="",
        )

    # --- STEP 4: Aggregate Metrics with Robust Type Casting ---
    sessions_done = len(sessions)
    total_lift = 0.0

    for s in sessions:
        try:
            pre_score = s.get("anxiety_level_before")
            post_score = s.get("anxiety_level_after")

            # Safe parsing: Guards against unexpected string formats or None values in rows
            val_pre = float(pre_score) if pre_score is not None else 0.0
            val_post = float(post_score) if post_score is not None else 0.0

            total_lift += (val_post - val_pre) 
        except (ValueError, TypeError):
            continue

    # Division-by-zero protection guard
    avg_lift_per_session = float(round(total_lift / sessions_done, 1)) if sessions_done > 0 else 0.0

    # --- STEP 5: Run AI Inference Pipeline with Format Guards ---
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

    validated_insight = None

    try:
        raw_text = await asyncio.wait_for(
            asyncio.to_thread(
                _chat,
                system="You are a precise JSON coaching metrics assistant.",
                user=prompt,
            ),
            timeout=4.0,
        )

        if raw_text:
            cleaned_text = raw_text.strip()
            # Intercept and clean accidental markdown wrappers if returned by the LLM
            if cleaned_text.startswith("```"):
                lines = cleaned_text.splitlines()
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    lines = lines[1:-1]
                cleaned_text = "\n".join(lines).strip()

            parsed_json = json.loads(cleaned_text)
            validated_insight = ProgressInsight(**parsed_json)
    except (asyncio.TimeoutError, Exception) as err:
        logger.error(f"OpenAI progress insight calculation failed: {repr(err)}")

    # Strict Fallback Check: Enforce local backup generation if AI fails or returns empty fields
    if not validated_insight or not getattr(validated_insight, "key_insight", None):
        validated_insight = execute_fallback_logic(sessions_done, avg_lift_per_session)

    clean_insight_str = " ".join(validated_insight.key_insight.split()[:20])

    # --- STEP 6: Package Safe Payload Response ---
    return ProgressResponse(
        sessions_done=sessions_done,
        day_streak=day_streak,
        avg_lift_per_session=avg_lift_per_session,
        key_insight=clean_insight_str,
    )
