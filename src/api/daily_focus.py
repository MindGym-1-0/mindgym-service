from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, UTC
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, status

# Upgraded to modern SDK namespace
from google import genai
from pydantic import BaseModel

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client

# Reuse your streak increment logic built from Part 2 directly
from src.api.streaks import increment_user_streak
from src.types.daily_focus import ActionType, DailyFocusResponse, GeminiDailyFocusOutput

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the standard Client. It picks up your GEMINI_API_KEY environment variable.
ai_client = genai.Client()


def execute_fallback_logic(context: Dict[str, Any]) -> GeminiDailyFocusOutput:
    """Generates a highly contextual fallback response if Gemini fails or times out."""
    logger.warning("Executing local fallback logic for daily focus generation.")
    today = date.today()

    # 1. Check for urgent interview in the next 2 days
    upcoming_interviews = context.get("interviews", [])
    for iv in upcoming_interviews:
        try:
            iv_date = datetime.strptime(
                iv["interview_date"].split("T")[0], "%Y-%m-%d"
            ).date()
            if today <= iv_date <= (today + timedelta(days=2)):
                return GeminiDailyFocusOutput(
                    action_1_text=f"Prepare for your upcoming interview with {iv.get('company')} for the {iv.get('role')} role.",
                    action_1_type=ActionType.PREPARE_INTERVIEW,
                    action_2_text="Review your application details and core engineering projects.",
                    action_2_type=ActionType.GENERIC_PIPELINE,
                )
        except Exception:
            continue

    # 2. Check for stagnant applications (> 14 days)
    active_jobs = context.get("jobs", [])
    for job in active_jobs:
        try:
            last_moved = datetime.strptime(
                job["last_moved_at"].split("T")[0], "%Y-%m-%d"
            ).date()
            if (today - last_moved).days > 14:
                return GeminiDailyFocusOutput(
                    action_1_text=f"Follow up with the hiring team or recruiter at {job.get('company')} regarding your {job.get('role')} application.",
                    action_1_type=ActionType.FOLLOW_UP,
                    action_2_text="Keep looking for new technical opportunities to fill your pipeline.",
                    action_2_type=ActionType.ADD_APPLICATIONS,
                )
        except Exception:
            continue

    # 3. Check for low pipeline numbers (Fixed: schema holds stage as lowercase "applied")
    applied_count = sum(1 for j in active_jobs if j.get("stage") == "applied")
    if applied_count < 3:
        return GeminiDailyFocusOutput(
            action_1_text="Find and apply to at least 2 new jobs today to keep your application pipeline healthy.",
            action_1_type=ActionType.ADD_APPLICATIONS,
            action_2_text=None,
            action_2_type=None,
        )

    # 4. Total safe default
    return GeminiDailyFocusOutput(
        action_1_text="Review your open applications and plan out outreach targets for the week.",
        action_1_type=ActionType.GENERIC_PIPELINE,
        action_2_text=None,
        action_2_type=None,
    )


@router.post(
    "/generate",
    response_model=DailyFocusResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate daily action focus items using pipeline context",
)
async def generate_daily_focus(current_user_id: CurrentUserId, token: CurrentUserToken):
    today_str = date.today().strftime("%Y-%m-%d")
    sb = get_supabase_user_client(token)
    user_uuid_str = str(current_user_id)

    # STEP 1: Fetch multi-table context from Supabase via non-blocking worker threads
    try:
        user_res = await asyncio.to_thread(
            sb.table("users")
            .select("goal, stage, anxiety_level")
            .eq("id", user_uuid_str)
            .execute
        )
        user_profile = user_res.data[0] if user_res.data else {}

        jobs_res = await asyncio.to_thread(
            sb.table("jobs")
            .select("company, role, stage, last_moved_at")
            .eq("user_id", user_uuid_str)
            .is_("outcome", "null")
            .order("last_moved_at", descending=True)
            .execute
        )
        active_jobs = jobs_res.data or []

        interviews_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("company, role, interview_date")
            .eq("user_id", user_uuid_str)
            .gte("interview_date", today_str)
            .order("interview_date", ascending=True)
            .limit(2)
            .execute
        )
        upcoming_interviews = interviews_res.data or []

        # Fixed: selected anxiety_level_delta instead of old mood_delta field
        sessions_res = await asyncio.to_thread(
            sb.table("ai_sessions")
            .select("preparation_for, anxiety_level_delta, completed_at")
            .eq("user_id", user_uuid_str)
            .is_("completed_at", "not.null")
            .order("completed_at", descending=True)
            .limit(3)
            .execute
        )
        recent_sessions = sessions_res.data or []

        streak_res = await asyncio.to_thread(
            sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_uuid_str)
            .execute
        )
        current_streak = (
            streak_res.data[0].get("current_streak", 0) if streak_res.data else 0
        )
    except Exception as db_err:
        logger.error(
            f"Failed to fetch user context tables from Supabase: {str(db_err)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up user metadata context.",
        )

    context = {
        "profile": user_profile,
        "jobs": active_jobs,
        "interviews": upcoming_interviews,
        "sessions": recent_sessions,
        "streak": current_streak,
    }

    # STEP 2: Build the prompt
    prompt = f"""
    You are an expert, highly personalized AI Job Search Assistant for a software engineer.
    Analyze the user's specific application pipeline below and return exactly 1 or 2 actions for today.

    CRITICAL PRODUCT REQUIREMENT: Generic output like "apply to more jobs" or "check your status" is a defect.
    You MUST reference specific companies, roles, timeline conditions, or interview opportunities present in the raw data context.

    --- USER PIPELINE CONTEXT ---
    User Profile: {json.dumps(user_profile)}
    Active Applications: {json.dumps(active_jobs)}
    Upcoming Interviews: {json.dumps(upcoming_interviews)}
    Recent App Interaction Sessions: {json.dumps(recent_sessions)}
    Current Daily Engagement Streak: {current_streak} days
    Current Date: {today_str}

    --- BUSINESS RULE PRIORITY HEURISTICS ---
    1. Urgent Interview Focus: If an interview is scheduled in the next 2 days, action_1 MUST guide preparation for that specific company and role.
    2. Stagnant Applications: If an application has sat in its current stage without moving for more than 14 days, prioritize an outreach or follow-up action naming that company.
    3. Low Pipeline Volume: If there are fewer than 3 active items in the 'applied' stage, prioritize adding new job targets.
    4. Feedback & Debrief Loops: If an application's stage was advanced recently but no post-session debrief was logged, prioritize a debrief logging task.
    """

    # STEP 3 & 4: Call Gemini with strict formatting validation and a 4-second timeout limit
    validated_output: Optional[GeminiDailyFocusOutput] = None
    try:

        async def call_gemini_api():
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": GeminiDailyFocusOutput,
                    },
                ),
            )
            return response.text

        raw_text = await asyncio.wait_for(call_gemini_api(), timeout=4.0)
        parsed_json = json.loads(raw_text.strip())
        validated_output = GeminiDailyFocusOutput(**parsed_json)
    except (asyncio.TimeoutError, Exception) as err:
        logger.error(
            f"Gemini generation failure or timeout window exceeded: {repr(err)}"
        )
        validated_output = execute_fallback_logic(context)

    if not validated_output or not validated_output.action_1_text:
        validated_output = execute_fallback_logic(context)

    # STEP 5 & 6: Save/Upsert and Return
    try:
        focus_payload = {
            "user_id": user_uuid_str,
            "date": today_str,
            "action_1_text": validated_output.action_1_text,
            "action_1_type": (
                validated_output.action_1_type.value
                if hasattr(validated_output.action_1_type, "value")
                else validated_output.action_1_type
            ),
            "action_2_text": validated_output.action_2_text,
            "action_2_type": (
                validated_output.action_2_type.value
                if validated_output.action_2_type
                and hasattr(validated_output.action_2_type, "value")
                else validated_output.action_2_type
            ),
            "updated_at": datetime.utcnow().isoformat(),
        }

        existing_check = await asyncio.to_thread(
            sb.table("daily_focus")
            .select("id")
            .eq("user_id", user_uuid_str)
            .eq("date", today_str)
            .execute
        )

        if existing_check.data:
            record_id = existing_check.data[0]["id"]
            db_result = await asyncio.to_thread(
                sb.table("daily_focus")
                .update(focus_payload)
                .eq("id", record_id)
                .execute
            )
        else:
            focus_payload["created_at"] = datetime.utcnow().isoformat()
            db_result = await asyncio.to_thread(
                sb.table("daily_focus").insert(focus_payload).execute
            )

        return db_result.data[0]
    except Exception as save_err:
        logger.error(
            f"Error saving daily focus context mapping record: {str(save_err)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated focus plan record.",
        )


# =====================================================================
# PART 5: COMPLETE ENDPOINTS (DAILY FOCUS TASK TRACKING SWAP-SYSTEM)
# =====================================================================


class DailyFocusCompleteRequest(BaseModel):
    action_id: str  # Expected values: "action_1" or "action_2"


class DailyFocusCompleteResponse(BaseModel):
    success: bool
    current_streak: int
    milestone: Optional[str] = None


@router.post(
    "/complete",
    response_model=DailyFocusCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a specific daily focus action item as completed and update streak",
)
async def complete_daily_focus(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    payload: DailyFocusCompleteRequest = Body(...),
):
    sb = get_supabase_user_client(token)
    user_uuid_str = str(current_user_id)
    today_str = date.today().strftime("%Y-%m-%d")

    if payload.action_id not in ["action_1", "action_2"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action_id. Must be 'action_1' or 'action_2'.",
        )

    # 1. Fetch today's focus row to check state existence
    try:
        existing_check = await asyncio.to_thread(
            sb.table("daily_focus")
            .select("id, action_1_completed, action_2_completed")
            .eq("user_id", user_uuid_str)
            .eq("date", today_str)
            .execute
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database lookup failure: {str(err)}",
        )

    if not existing_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily focus action plan found for today.",
        )

    record = existing_check.data[0]
    record_id = record["id"]

    # Check if target action field is already marked true
    target_field = f"{payload.action_id}_completed"
    if record.get(target_field) is True:
        # Already completed; fetch current streak status without duplicate increments
        streak_res = await asyncio.to_thread(
            sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_uuid_str)
            .execute
        )
        current_streak = streak_res.data[0]["current_streak"] if streak_res.data else 0
        return DailyFocusCompleteResponse(
            success=True, current_streak=current_streak, milestone=None
        )

    # 2. Update the target column inside daily_focus table structure
    try:
        update_payload = {
            target_field: True,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        await asyncio.to_thread(
            sb.table("daily_focus").update(update_payload).eq("id", record_id).execute
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update action task completion state: {str(err)}",
        )

    # 3. Reuse your streak increment logic built during Part 2
    try:
        streak_data = await increment_user_streak(user_uuid_str, sb)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action completed, but streak calculation failed: {str(err)}",
        )

    return DailyFocusCompleteResponse(
        success=True,
        current_streak=streak_data.get("current_streak", 0),
        milestone=streak_data.get("milestone"),
    )
