from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.openai_service import _chat
from src.lib.supabase import get_supabase_user_client
from src.types.insight import (
    HiringFunnelGap,
    InsightsResponse,
    SecondaryInsightItem,
    TopInsightItem,
)

router = APIRouter(prefix="/api/insights", tags=["Insights"])
logger = logging.getLogger("mindgym")


def execute_fallback_insights(ctx: dict) -> InsightsResponse:
    """Builds structured fallback local insights if the OpenAI execution
    times out or encounters parsing discrepancies.
    """
    lift = ctx.get("overall_avg_lift", 0.0)
    top = [
        TopInsightItem(
            text="Consistency Baseline Established",
            detail=f"Completed {ctx['total_sessions']} focus exercises "
            f"with an average anxiety delta reduction of {lift}.",
            highlight=True,
        ),
        TopInsightItem(
            text="Application Momentum Stable",
            detail=f"Tracking {ctx['applications_count']} active opportunities "
            f"within your job funnel.",
            highlight=True,
        ),
    ]

    sec = [
        SecondaryInsightItem(text="Keep utilizing structured calming routines."),
        SecondaryInsightItem(text="Review your upcoming mock test schedules."),
        SecondaryInsightItem(text="Consistency across weeks preserves retention."),
    ]

    gap = HiringFunnelGap(
        title="Hiring Funnel Gap Identified",
        body="Continue expanding application streams to hit metric baselines.",
        based_on=f"{ctx['total_sessions']} sessions · Delta {lift} · Active 100%",
    )

    return InsightsResponse(
        top_insights=top, secondary_insights=sec, hiring_funnel_gap=gap
    )


# --- ANALYTICS PIPELINE ---
def calculate_insights_context(supabase_client, user_id: str) -> dict | None:
    """Aggregates multi-table tracking context data from Supabase."""
    try:
        user_res = (
            supabase_client.table("users")
            .select("target_role_category, employment_status, emotional_challenge")
            .eq("id", user_id)
            .execute()
        )
        user_data = user_res.data[0] if user_res.data else {}

        # FIX 1: Changed "stage" to "status" to match actual column layout
        jobs_res = (
            supabase_client.table("jobs")
            .select("id, status")
            .eq("user_id", user_id)
            .execute()
        )
        interviews_res = (
            supabase_client.table("interviews")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )

        # FIX 2: Replaced .eq("completed", True) with timestamp presence filter
        sessions_res = (
            supabase_client.table("ai_sessions")
            .select("*")
            .eq("user_id", user_id)
            .not_.is_("completed_at", "null")
            .execute()
        )
        sessions = sessions_res.data or []
    except Exception as e:
        logger.error(f"Failed to fetch insights context: {str(e)}")
        return None

    if len(sessions) < 3:
        return None

    total_sessions = len(sessions)

    lifts = []
    for s in sessions:
        before = s.get("anxiety_level_before")
        after = s.get("anxiety_level_after")
        if before is not None and after is not None:
            lifts.append(float(before) - float(after))

    avg_lift = sum(lifts) / len(lifts) if lifts else 0.0

    morning_lifts = []
    evening_lifts = []
    type_lifts = {}

    # FIX 3: Removed dead emotional_challenge loop from here as it lives on user_data
    for s in sessions:
        s_type = s.get("preparation_for")
        before = s.get("anxiety_level_before")
        after = s.get("anxiety_level_after")

        if s_type and before is not None and after is not None:
            delta = float(before) - float(after)
            type_lifts.setdefault(s_type, []).append(delta)

        if s.get("completed_at"):
            try:
                dt = datetime.fromisoformat(
                    s["completed_at"].replace("Z", "+00:00")
                )
                if before is not None and after is not None:
                    delta = float(before) - float(after)
                    if dt.hour < 10:
                        morning_lifts.append(delta)
                    elif dt.hour >= 18:
                        evening_lifts.append(delta)
            except Exception:
                continue

    avg_morning = sum(morning_lifts) / len(morning_lifts) if morning_lifts else None
    avg_evening = sum(evening_lifts) / len(evening_lifts) if evening_lifts else None

    highest_type = None
    highest_type_avg = float("-inf")
    for t, t_lifts in type_lifts.items():
        t_avg = sum(t_lifts) / len(t_lifts)
        if t_avg > highest_type_avg:
            highest_type_avg = t_avg
            highest_type = t

    now = datetime.now(UTC)
    two_weeks_ago = now - timedelta(days=14)

    def get_avg_dimensions(filtered_sessions):
        dims = {"confidence": 0.0, "clarity": 0.0, "calmness": 0.0, "focus": 0.0}
        counts = {"confidence": 0, "clarity": 0, "calmness": 0, "focus": 0}
        for s in filtered_sessions:
            for k in dims:
                val = s.get(f"post_{k}") or s.get(k)
                if val is not None:
                    dims[k] += float(val)
                    counts[k] += 1
        return {
            k: (dims[k] / counts[k] if counts[k] > 0 else None) for k in dims
        }

    current_dims = get_avg_dimensions(sessions)

    past_sessions = []
    for s in sessions:
        if s.get("completed_at"):
            try:
                dt = datetime.fromisoformat(
                    s["completed_at"].replace("Z", "+00:00")
                )
                if dt <= two_weeks_ago:
                    past_sessions.append(s)
            except Exception:
                continue
    past_dims = get_avg_dimensions(past_sessions)

    ctx = {
        "total_sessions": total_sessions,
        "overall_avg_lift": round(avg_lift, 2),
        "applications_count": len(jobs_res.data or []),
        "interviews_count": len(interviews_res.data or []),
    }

    if user_data.get("target_role_category"):
        ctx["target_role_category"] = user_data["target_role_category"]
    if user_data.get("employment_status"):
        ctx["employment_status"] = user_data["employment_status"]
    if user_data.get("emotional_challenge"):
        ctx["emotional_challenge"] = user_data["emotional_challenge"]

    if avg_morning is not None:
        ctx["avg_lift_morning_before_10am"] = round(avg_morning, 2)
    if avg_evening is not None:
        ctx["avg_lift_evening_after_6pm"] = round(avg_evening, 2)
    if highest_type:
        ctx["session_type_with_highest_avg_lift"] = highest_type

    ctx["current_metrics"] = {
        k: round(v, 2) for k, v in current_dims.items() if v is not None
    }
    ctx["metrics_two_weeks_ago"] = {
        k: round(v, 2) for k, v in past_dims.items() if v is not None
    }

    return ctx


@router.get("", response_model=InsightsResponse)
async def get_insights(
    current_user_id: Annotated[UUID, Depends(CurrentUserId)],
    token: Annotated[str, Depends(CurrentUserToken)],
):
    """Generates two tiers of AI metrics and funnel insights via OpenAI."""
    supabase_client = get_supabase_user_client(token)

    context_data = await asyncio.to_thread(
        calculate_insights_context, supabase_client, str(current_user_id)
    )

    if context_data is None:
        return InsightsResponse(
            top_insights=[], secondary_insights=[], hiring_funnel_gap=None
        )

    prompt = f"""
    You are the core analytical engine of MindGym.
    Analyze this user context to generate tailored behavioral insights.

    USER DATA CONTEXT:
    {json.dumps(context_data, indent=2)}

    PROMPT INSTRUCTIONS AND RULES:
    1. Return JSON ONLY matching this exact structure:
    {{
      "top_insights": [
        {{"text": "...", "detail": "..."}},
        {{"text": "...", "detail": "..."}}
      ],
      "secondary_insights": [
        {{"text": "..."}},
        {{"text": "..."}},
        {{"text": "..."}}
      ],
      "hiring_funnel_gap": {{
        "title": "Hiring Funnel Gap Identified",
        "body": "...",
        "based_on": "..."
      }}
    }}

    2. RULES FOR SECTIONS:
       - `top_insights`: Exactly 2 items. Text max 8 words. Supporting detail line
         must contain real metrics.
       - `secondary_insights`: Exactly 3 items. Short punchy statements.
       - `hiring_funnel_gap.body`: 2-3 action-oriented sentences.
       - `hiring_funnel_gap.based_on`: Must use format layout strictly:
         "N sessions · Metric X% · Metric Y%"

    Do not include markdown wrappers (like ```json). Return raw JSON directly.
    """

    try:
        clean_text = await asyncio.wait_for(
            asyncio.to_thread(
                _chat,
                system="You are a precise JSON insights engine.",
                user=prompt,
            ),
            timeout=10.0,
        )

        if clean_text is None:
            raise ValueError("OpenAI backend wrapper returned an empty string.")

        parsed = json.loads(clean_text)

        for item in parsed.get("top_insights", []):
            item["highlight"] = True

        return InsightsResponse(**parsed)

    except (Exception, asyncio.TimeoutError) as err:
        logger.warning(f"OpenAI insight analysis pipeline hit fallback: {str(err)}")
        return execute_fallback_insights(context_data)
