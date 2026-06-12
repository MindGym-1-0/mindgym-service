from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.streaks import increment_user_streak
from src.lib.auth import CurrentUserId, CurrentUserToken
# Fixed: Swapped out genai for the standardized openai helper from PR #64
from src.lib.openai_service import _chat
from src.lib.supabase import get_supabase_user_client
from src.types.daily_focus import (
    ActionType,
    DailyFocusResponse,
    GeminiDailyFocusOutput,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def execute_fallback_logic(context: Dict[str, Any]) -> GeminiDailyFocusOutput:
    """Generates a highly contextual fallback response if OpenAI fails."""
    logger.warning("Executing local fallback logic for daily focus.")
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
                    action_1_text=(
                        f"Prepare for your upcoming interview with "
                        f"{iv.get('company')} for the {iv.get('role')} role."
                    ),
                    action_1_type=ActionType.PREPARE_INTERVIEW,
                    action_2_text=(
                        "Review your application details and core "
                        "engineering projects."
                    ),
                    action_2_type=ActionType.GENERIC_PIPELINE,
                )
        except Exception as e:
            logger.warning(f"Skipping row due to interview parse error: {e}")
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
                    action_1_text=(
                        f"Follow up with the hiring team or recruiter at "
                        f"{job.get('company')} regarding your "
                        f"{job.get('role')} application."
                    ),
                    action_1_type=ActionType.FOLLOW_UP,
                    action_2_text=(
                        "Keep looking for new technical opportunities "
                        "to fill your pipeline."
                    ),
                    action_2_type=ActionType.ADD_APPLICATIONS,
                )
        except Exception as e:
            logger.warning(f"Skipping row due to job status parse error: {e}")
            continue

    # 3. Check for low pipeline numbers (Schema holds lowercase status column)
    applied_count = sum(1 for j in active_jobs if j.get("status") == "applied")
    if applied_count < 3:
        return GeminiDailyFocusOutput(
            action_1_text=(
                "Find and apply to at least 2 new jobs today to keep "
                "your application pipeline healthy."
            ),
            action_1_type=ActionType.ADD_APPLICATIONS,
            action_2_text=None,
            action_2_type=None,
        )

    # 4. Total safe default
    return GeminiDailyFocusOutput(
        action_1_text=(
            "Review your open applications and plan out outreach "
            "targets for the week."
        ),
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
async def generate_daily_focus(
    current_user_id: CurrentUserId, token: CurrentUserToken
):
    today_str = date.today().strftime("%Y-%m-%d")
    sb = get_supabase_user_client(token)
    user_uuid_str = str(current_user_id)

    # STEP 1: Fetch multi-table context from Supabase
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
            .select("company, role, status, last_moved_at")
            .eq("user_id", user_uuid_str)
            .is_("outcome", "null")
            .order("last_moved_at", desc=True)
            .execute
        )
        active_jobs = jobs_res.data or []

        interviews_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("company, role, interview_date")
            .eq("user_id", user_uuid_str)
            .gte("interview_date", today_str)
            .order("interview_date")
            .limit(2)
            .execute
        )
        upcoming_interviews = interviews_res.data or []

        sessions_res = await asyncio.to_thread(
            sb.table("ai_sessions")
            .select("preparation_for, anxiety_level_delta, completed_at")
            .eq("user_id", user_uuid_str)
            .not_.is_("completed_at", "null")
            .order("completed_at", desc=True)
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
            streak_res.data[0].get("current_streak", 0)
            if streak_res.data
            else 0
        )
    except Exception as db_err:
        logger.error(f"Failed to fetch user context tables: {str(db_err)}")
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
    You are an expert, highly personalized AI Job Assistant for an engineer.
    Analyze the user's specific application pipeline below and return targets.

    CRITICAL REQUIREMENT: Generic output like "apply to more jobs" is a defect.
    You MUST reference specific companies, roles, or raw data context.

    --- USER PIPELINE CONTEXT ---
    User Profile: {json.dumps(user_profile)}
    Active Applications: {json.dumps(active_jobs)}
    Upcoming Interviews: {json.dumps(upcoming_interviews)}
    Recent App Interaction Sessions: {json.dumps(recent_sessions)}
    Current Daily Engagement Streak: {current_streak} days
    Current Date: {today_str}

    --- BUSINESS RULE PRIORITY HEURISTICS ---
    1. Urgent Interview Focus: If interview is in next 2 days, action_1 targets.
    2. Stagnant Applications: If open items sat > 14 days, prioritize outreach.
    3. Low Pipeline Volume: If < 3 items are in 'applied' status, add new jobs.
    4. Feedback Loops: If stage moved but no debrief logged, prompt for debrief.
    """

    # STEP 3 & 4: Call OpenAI chat service with formatting validation
    validated_output: Optional[GeminiDailyFocusOutput] = None
    try:
        raw_text = await asyncio.wait_for(
            asyncio.to_thread(
                _chat,
                system=(
                    "You are a precise JSON career tracking metrics assistant. "
                    "You must output valid JSON matching the requested keys."
                ),
                user=prompt,
            ),
            timeout=4.0,
        )

        if raw_text is None:
            raise ValueError("OpenAI pipeline returned a null response string.")

        parsed_json = json.loads(raw_text.strip())
        validated_output = GeminiDailyFocusOutput(**parsed_json)
    except (asyncio.TimeoutError, Exception) as err:
        logger.error(f"OpenAI daily focus generation failed: {repr(err)}")
        validated_output = execute_fallback_logic(context)

    if not validated_output or not validated_output.action_1_text:
        validated_output = execute_fallback_logic(context)

    # STEP 5 & 6: Save/Upsert and Return Data Parameters
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
            "updated_at": datetime.now(UTC).isoformat(),
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
                .select("*")
                .execute
            )
        else:
            db_result = await asyncio.to_thread(
                sb.table("daily_focus")
                .insert(focus_payload)
                .select("*")
                .execute
            )

        return db_result.data[0]
    except Exception as save_err:
        logger.error(f"Error saving daily focus mapping record: {str(save_err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated focus plan record.",
        )


class DailyFocusCompleteRequest(BaseModel):
    action_id: str


class DailyFocusCompleteResponse(BaseModel):
    success: bool
    current_streak: int
    milestone: Optional[str] = None


@router.post(
    "/complete",
    response_model=DailyFocusCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark focus item completed and increment user streak values",
)
async def complete_daily_focus(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    payload: DailyFocusCompleteRequest,
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
        streak_res = await asyncio.to_thread(
            sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_uuid_str)
            .execute
        )
        current_streak = (
            streak_res.data[0]["current_streak"] if streak_res.data else 0
        )
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
            sb.table("daily_focus")
            .update(update_payload)
            .eq("id", record_id)
            .execute
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task completion state: {str(err)}",
        )

    # 3. Parameter ordering matches structural definition
    try:
        streak_data = await increment_user_streak(sb, user_uuid_str)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action finished, but streak update failed: {str(err)}",
        )

    return DailyFocusCompleteResponse(
        success=True,
        current_streak=streak_data.get("current_streak", 0),
        milestone=streak_data.get("milestone"),
    )
