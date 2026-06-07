from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime, timedelta, UTC
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from google.genai import Client
from google.genai.errors import APIError
from pydantic import BaseModel, Field

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client

router = APIRouter(prefix="/api/insights", tags=["Insights"])
logger = logging.getLogger("mindgym")

ai_client = Client()


# --- RESPONSE SCHEMAS ---
class TopInsightItem(BaseModel):
    text: str = Field(..., description="Short headline, max 8 words.")
    detail: str = Field(..., description="Supporting detail with metrics.")
    highlight: bool = True


class SecondaryInsightItem(BaseModel):
    text: str = Field(..., description="Short insight statement.")


class HiringFunnelGap(BaseModel):
    title: str = Field("Hiring Funnel Gap Identified")
    body: str = Field(..., description="2-3 actionable sentences.")
    based_on: str = Field(..., description="Format: N sessions · X% · Y%")


class InsightsResponse(BaseModel):
    top_insights: List[TopInsightItem]
    secondary_insights: List[SecondaryInsightItem]
    hiring_funnel_gap: Optional[HiringFunnelGap] = None


# --- ANALYTICS PIPELINE ---
def calculate_insights_context(supabase_client, user_id: str) -> dict | None:
    """Aggregates multi-table tracking context data from Supabase."""
    user_res = (
        supabase_client.table("users")
        .select("goal, stage, anxiety_level, onboarding_data")
        .eq("id", user_id)
        .execute()
    )
    user_data = user_res.data[0] if user_res.data else {}

    jobs_res = (
        supabase_client.table("jobs")
        .select("id, stage")
        .eq("user_id", user_id)
        .execute()
    )
    interviews_res = (
        supabase_client.table("interviews")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )

    sessions_res = (
        supabase_client.table("ai_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("completed", True)
        .execute()
    )
    sessions = sessions_res.data or []

    if len(sessions) < 3:
        return None

    total_sessions = len(sessions)
    lifts = [
        (s["post_score"] - s["pre_score"])
        for s in sessions
        if s.get("post_score") is not None and s.get("pre_score") is not None
    ]
    avg_lift = sum(lifts) / len(lifts) if lifts else 0.0

    p1_lifts = [
        (s["post_score"] - s["pre_score"])
        for s in sessions
        if s.get("phase_1_complete") is True
        and s.get("post_score") is not None
        and s.get("pre_score") is not None
    ]
    no_p1_lifts = [
        (s["post_score"] - s["pre_score"])
        for s in sessions
        if not s.get("phase_1_complete")
        and s.get("post_score") is not None
        and s.get("pre_score") is not None
    ]
    avg_p1_lift = sum(p1_lifts) / len(p1_lifts) if p1_lifts else None
    avg_no_p1_lift = sum(no_p1_lifts) / len(no_p1_lifts) if no_p1_lifts else None

    morning_lifts = []
    evening_lifts = []
    emotions = []
    type_lifts = {}

    for s in sessions:
        if s.get("pre_emotion"):
            emotions.append(s["pre_emotion"])

        s_type = s.get("session_type")
        if (
            s_type
            and s.get("post_score") is not None
            and s.get("pre_score") is not None
        ):
            type_lifts.setdefault(s_type, []).append(
                s["post_score"] - s["pre_score"]
            )

        if s.get("completed_at"):
            try:
                dt = datetime.fromisoformat(
                    s["completed_at"].replace("Z", "+00:00")
                )
                lift = (
                    s["post_score"] - s["pre_score"]
                    if s.get("post_score") is not None
                    and s.get("pre_score") is not None
                    else None
                )
                if lift is not None:
                    if dt.hour < 10:
                        morning_lifts.append(lift)
                    elif dt.hour >= 18:
                        evening_lifts.append(lift)
            except Exception:
                continue

    avg_morning = sum(morning_lifts) / len(morning_lifts) if morning_lifts else None
    avg_evening = sum(evening_lifts) / len(evening_lifts) if evening_lifts else None
    freq_emotion = Counter(emotions).most_common(1)[0][0] if emotions else None

    highest_type = None
    highest_type_avg = -999.0
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

    if user_data.get("goal"):
        ctx["target_role_category"] = user_data["goal"]
    if user_data.get("stage"):
        ctx["employment_status"] = user_data["stage"]
    if user_data.get("anxiety_level"):
        ctx["emotional_challenge"] = user_data["anxiety_level"]

    if avg_p1_lift is not None:
        ctx["avg_lift_with_breathing_p1"] = round(avg_p1_lift, 2)
    if avg_no_p1_lift is not None:
        ctx["avg_lift_without_breathing_p1"] = round(avg_no_p1_lift, 2)
    if avg_morning is not None:
        ctx["avg_lift_morning_before_10am"] = round(avg_morning, 2)
    if avg_evening is not None:
        ctx["avg_lift_evening_after_6pm"] = round(avg_evening, 2)
    if freq_emotion:
        ctx["most_frequent_pre_session_emotion"] = freq_emotion
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
    """Generates two tiers of AI metrics and funnel insights via Gemini."""
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
        response = await asyncio.to_thread(
            ai_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )

        clean_text = response.text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("```json")[-1].split("```")[0].strip()

        parsed = json.loads(clean_text)

        for item in parsed.get("top_insights", []):
            item["highlight"] = True

        return InsightsResponse(**parsed)

    except (APIError, json.JSONDecodeError, KeyError, TypeError) as err:
        logger.error(f"Failed to generate automated insights: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "insight_generation_failed"},
        )