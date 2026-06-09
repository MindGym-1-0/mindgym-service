from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.openai_service import _chat
from src.lib.supabase import get_supabase_user_client
from src.types.weekly_mission import (
    WeeklyMissionInsight,
    WeeklyMissionGenerateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/weekly_mission", tags=["Weekly Mission"])


def get_target_monday() -> date:
    """Calculates the target Monday.

    If generated on a Sunday night, the coming Monday represents the actual
    operational week start.
    """
    today = datetime.now(timezone.utc).date()
    days_until_monday = (1 - today.isoweekday()) % 7
    return today + timedelta(days=days_until_monday)


def execute_fallback_generation(user_context: dict) -> dict:
    """Step 4 Fallback Engine: Explicitly builds 3 tailored actions via string
    formatting using pipeline metrics to ensure the client never encounters a
    processing failure.
    """
    active_jobs = user_context.get("active_jobs", [])
    total_applications = len(active_jobs)

    if total_applications < 3:
        act_1 = (
            "Target and submit at least 2 new backend engineering "
            "applications to expand your baseline pipeline."
        )
    else:
        act_1 = (
            f"Follow up on your existing {total_applications} open "
            "applications to gauge response momentum."
        )

    act_2 = (
        "Complete 2 practice mock sessions this week to initialize your "
        "competency tracking."
    )

    session_count = user_context.get("session_count", 0)
    if session_count < 2:
        act_3 = (
            "Book and complete a core system design mock study session "
            "to stabilize your weekly performance trends."
        )
    else:
        act_3 = (
            "Document post-session technical debrief notes across your "
            "upcoming interviews to protect your active tracking streak."
        )

    return {"action_1": act_1, "action_2": act_2, "action_3": act_3}


@router.post("/generate", response_model=WeeklyMissionGenerateResponse)
async def generate_weekly_mission(
    current_user_id: Annotated[UUID, Depends(CurrentUserId)],
    token: Annotated[str, Depends(CurrentUserToken)],
):
    supabase = get_supabase_user_client(token)
    user_id = str(current_user_id)

    # ------------------------------------------
    # STEP 1 — FETCH USER CONTEXT FROM SUPABASE
    # ------------------------------------------
    try:
        user_res = await asyncio.to_thread(
            supabase.table("users")
            .select("goal, stage")
            .eq("id", user_id)
            .execute
        )
        user_profile = (
            user_res.data[0]
            if user_res.data
            else {"goal": "General Placement", "stage": "Interviewing"}
        )

        jobs_res = await asyncio.to_thread(
            supabase.table("jobs")
            .select("id, status, last_moved_at")
            .eq("user_id", user_id)
            .is_("outcome", "null")
            .execute
        )
        active_jobs = jobs_res.data or []

        now_utc = datetime.now(timezone.utc)
        seven_days_ago = (now_utc - timedelta(days=7)).isoformat()

        sessions_res = await asyncio.to_thread(
            supabase.table("ai_sessions")
            .select("anxiety_level_delta")
            .eq("user_id", user_id)
            .gte("created_at", seven_days_ago)
            .execute
        )
        sessions_this_week = sessions_res.data or []
        session_count = len(sessions_this_week)

        avg_anxiety_delta = 0.0
        if session_count > 0:
            total_anxiety = sum(
                s.get("anxiety_level_delta", 0.0) for s in sessions_this_week
            )
            avg_anxiety_delta = total_anxiety / session_count

        prev_mission_res = await asyncio.to_thread(
            supabase.table("weekly_mission")
            .select("completion_count")
            .eq("user_id", user_id)
            .order("week_start_date", descending=True)
            .limit(1)
            .execute
        )
        prev_data = prev_mission_res.data
        prev_completion_count = (
            prev_data[0]["completion_count"] if prev_data else 0
        )

    except Exception as db_err:
        logger.error(f"Error compiling user mission parameters: {str(db_err)}")
        (
            active_jobs,
            session_count,
            prev_completion_count,
            avg_anxiety_delta,
        ) = ([], 0, 0, 0.0)
        user_profile = {"goal": "General Placement", "stage": "Interviewing"}

    context_package = {
        "user_profile": user_profile,
        "active_jobs": active_jobs,
        "session_count": session_count,
        "prev_completion_count": prev_completion_count,
        "avg_anxiety_delta": avg_anxiety_delta,
    }

    # ------------------------------------------
    # STEP 2 — BUILD THE OPENAI PROMPT
    # ------------------------------------------
    prompt = f"""
    You are an expert career performance optimization AI.
    Analyze the user's data to generate 3 actionable targets for next week.

    User Context:
    - Career Goal: {user_profile.get('goal')}
    - Application Stage: {user_profile.get('stage')}
    - Current Active Pipeline Jobs: {json.dumps(active_jobs, indent=2)}
    - Activity Volume This Week: {session_count} completed sessions
    - Completed Targets from Last Week: {prev_completion_count}/3

    Requirements and Structural Constraints:
    1. Focus heavily on pipeline gaps, performance gaps, or momentum drop-offs.
    2. Write highly concrete strings. Avoid generic platitudes.
    3. You MUST output raw JSON matching this structure exactly. No markdown blocks.

    {{
      "action_1": "...",
      "action_2": "...",
      "action_3": "..."
    }}
    """

    generated_actions = None

    # ------------------------------------------
    # STEP 3 & 4 — CALL OPENAI VIA ROUTED LOGIC
    # ------------------------------------------
    try:
        raw_text = await asyncio.wait_for(
            asyncio.to_thread(
                _chat,
                system="You are a precise JSON targets generation engine.",
                user=prompt,
            ),
            timeout=5.0,
        )

        if raw_text is None:
            raise ValueError("OpenAI pipeline failed to return response string.")

        parsed_response = json.loads(raw_text.strip())
        validated_insight = WeeklyMissionInsight(**parsed_response)

        generated_actions = {
            "action_1": validated_insight.action_1,
            "action_2": validated_insight.action_2,
            "action_3": validated_insight.action_3,
        }
    except (asyncio.TimeoutError, Exception) as gen_error:
        logger.error(f"OpenAI generation engine bypassed: {str(gen_error)}")
        generated_actions = execute_fallback_generation(context_package)

    # ------------------------------------------
    # STEP 5 — SAVE OR UPDATE SUPABASE RECORD
    # ------------------------------------------
    target_monday = get_target_monday()

    upsert_payload = {
        "user_id": user_id,
        "week_start_date": target_monday.isoformat(),
        "action_1": generated_actions["action_1"],
        "action_2": generated_actions["action_2"],
        "action_3": generated_actions["action_3"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    existing_row = await asyncio.to_thread(
        supabase.table("weekly_mission")
        .select("*")
        .eq("user_id", user_id)
        .eq("week_start_date", target_monday.isoformat())
        .execute
    )

    if existing_row.data:
        res = await asyncio.to_thread(
            supabase.table("weekly_mission")
            .update(upsert_payload)
            .eq("id", existing_row.data[0]["id"])
            .select("*")
            .execute
        )
    else:
        upsert_payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        upsert_payload["action_1_completed"] = False
        upsert_payload["action_2_completed"] = False
        upsert_payload["action_3_completed"] = False
        upsert_payload["completion_count"] = 0
        res = await asyncio.to_thread(
            supabase.table("weekly_mission")
            .insert(upsert_payload)
            .select("*")
            .execute
        )

    # ------------------------------------------
    # STEP 6 — RETURN MAPPED RESPONSE RECORD
    # ------------------------------------------
    record = res.data[0]

    raw_week_date = record["week_start_date"]
    parsed_week_date = (
        date.fromisoformat(raw_week_date)
        if isinstance(raw_week_date, str)
        else raw_week_date
    )

    raw_gen_at = record["generated_at"]
    parsed_gen_at = (
        datetime.fromisoformat(raw_gen_at.replace("Z", "+00:00"))
        if isinstance(raw_gen_at, str)
        else raw_gen_at
    )

    raw_up_at = record["updated_at"]
    parsed_up_at = (
        datetime.fromisoformat(raw_up_at.replace("Z", "+00:00"))
        if isinstance(raw_up_at, str)
        else raw_up_at
    )

    return WeeklyMissionGenerateResponse(
        id=str(record["id"]),
        user_id=str(record["user_id"]),
        week_start_date=parsed_week_date,
        action_1=record["action_1"],
        action_1_completed=record["action_1_completed"],
        action_2=record["action_2"],
        action_2_completed=record["action_2_completed"],
        action_3=record["action_3"],
        action_3_completed=record["action_3_completed"],
        completion_count=record["completion_count"],
        generated_at=parsed_gen_at,
        updated_at=parsed_up_at,
    )


class WeeklyMissionCompleteRequest(BaseModel):
    mission_item_id: str


class WeeklyMissionCompleteResponse(BaseModel):
    success: bool
    items_completed: int
    total_items: int = 3


@router.post(
    "/complete",
    response_model=WeeklyMissionCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a specific item as completed and increment tracker counter",
)
async def complete_weekly_mission(
    current_user_id: Annotated[UUID, Depends(CurrentUserId)],
    token: Annotated[str, Depends(CurrentUserToken)],
    payload: WeeklyMissionCompleteRequest,
):
    supabase = get_supabase_user_client(token)
    user_id = str(current_user_id)
    target_monday_str = get_target_monday().isoformat()

    if payload.mission_item_id not in ["action_1", "action_2", "action_3"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mission_item_id. Must be action_1, _2, or _3.",
        )

    existing_row = await asyncio.to_thread(
        supabase.table("weekly_mission")
        .select("*")
        .eq("user_id", user_id)
        .eq("week_start_date", target_monday_str)
        .execute
    )

    if not existing_row.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly mission structure initialized for this week.",
        )

    record = existing_row.data[0]
    record_id = record["id"]

    target_completed_field = f"{payload.mission_item_id}_completed"

    if record.get(target_completed_field) is True:
        return WeeklyMissionCompleteResponse(
            success=True,
            items_completed=record.get("completion_count", 0),
            total_items=3,
        )

    new_completion_count = record.get("completion_count", 0) + 1
    if new_completion_count > 3:
        new_completion_count = 3

    update_payload = {
        target_completed_field: True,
        "completion_count": new_completion_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await asyncio.to_thread(
            supabase.table("weekly_mission")
            .update(update_payload)
            .eq("id", record_id)
            .execute
        )
    except Exception as save_err:
        logger.error(f"Failed writing update payload ledger: {str(save_err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update weekly mission target completion counts.",
        )

    return WeeklyMissionCompleteResponse(
        success=True,
        items_completed=new_completion_count,
        total_items=3,
    )
