# src/api/weekly_mission.py

from __future__ import annotations
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from src.lib import config
from src.lib.auth_dependencies import get_current_user
from src.types.weekly_mission import WeeklyMissionGenerateResponse, GeminiMissionOutput

# Modern Google GenAI SDK imports
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
router = APIRouter()


def get_supabase_client() -> Client:
    url = config.supabase_url()
    service_key = config.supabase_service_role_key()
    if not url or not service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase infrastructure keys are missing.",
        )
    return create_client(url, service_key)


def get_target_monday() -> date:
    """
    Calculates the target Monday. If generated on a Sunday night,
    the coming Monday represents the actual operational week start.
    """
    today = datetime.now(timezone.utc).date()
    days_until_monday = (1 - today.isoweekday()) % 7
    return today + timedelta(days=days_until_monday)


def execute_fallback_generation(user_context: dict) -> dict:
    """
    Step 4 Fallback Engine: Explicitly builds 3 tailored actions via string formatting
    using pipeline metrics to ensure the client never encounters a processing failure.
    """
    active_jobs = user_context.get("active_jobs", [])
    total_applications = len(active_jobs)

    if total_applications < 3:
        act_1 = "Target and submit at least 2 new backend engineering applications to expand your baseline pipeline."
    else:
        act_1 = f"Follow up on your existing {total_applications} open applications to gauge response momentum."

    perf_logs = user_context.get("performance_logs", [])
    if perf_logs:
        act_2 = "Review your recent session diagnostic breakdowns specifically targeting improvement in technical execution."
    else:
        act_2 = "Complete 2 practice mock sessions this week to initialize your competency tracking performance logs."

    session_count = user_context.get("session_count", 0)
    if session_count < 2:
        act_3 = "Book and complete a core system design mock study session to stabilize your weekly performance trends."
    else:
        act_3 = "Document post-session technical debrief notes across your upcoming interviews to protect your active tracking streak."

    return {"action_1": act_1, "action_2": act_2, "action_3": act_3}


@router.post("/generate", response_model=WeeklyMissionGenerateResponse)
async def generate_weekly_mission(
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid active user session.",
        )

    # ----------------==========================
    # STEP 1 ΓÇö FETCH USER CONTEXT FROM SUPABASE
    # --------------------------------==========
    try:
        user_res = (
            supabase.table("users").select("goal, stage").eq("id", user_id).execute()
        )
        user_profile = (
            user_res.data[0]
            if user_res.data
            else {"goal": "General Placement", "stage": "Interviewing"}
        )

        jobs_res = (
            supabase.table("applications")
            .select("id, stage, last_moved_at")
            .eq("user_id", user_id)
            .execute()
        )
        active_jobs = jobs_res.data or []

        perf_res = (
            supabase.table("performance_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", descending=True)
            .limit(4)
            .execute()
        )
        performance_logs = perf_res.data or []

        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        sessions_res = (
            supabase.table("sessions")
            .select("mood_delta")
            .eq("user_id", user_id)
            .gte("created_at", seven_days_ago)
            .execute()
        )
        sessions_this_week = sessions_res.data or []
        session_count = len(sessions_this_week)

        avg_mood_delta = 0.0
        if session_count > 0:
            avg_mood_delta = (
                sum(s.get("mood_delta", 0.0) for s in sessions_this_week)
                / session_count
            )

        prev_mission_res = (
            supabase.table("weekly_mission")
            .select("completion_count")
            .eq("user_id", user_id)
            .order("week_start_date", descending=True)
            .limit(1)
            .execute()
        )
        prev_completion_count = (
            prev_mission_res.data[0]["completion_count"] if prev_mission_res.data else 0
        )

    except Exception as db_err:
        logger.error(f"Error compiling user mission context parameters: {str(db_err)}")
        (
            active_jobs,
            performance_logs,
            session_count,
            prev_completion_count,
            avg_mood_delta,
        ) = ([], [], 0, 0, 0.0)
        user_profile = {"goal": "General Placement", "stage": "Interviewing"}

    context_package = {
        "user_profile": user_profile,
        "active_jobs": active_jobs,
        "performance_logs": performance_logs,
        "session_count": session_count,
        "prev_completion_count": prev_completion_count,
        "avg_mood_delta": avg_mood_delta,
    }

    # ----------------==========================
    # STEP 2 ΓÇö BUILD THE GEMINI PROMPT
    # --------------------------------==========
    prompt = f"""
    You are an expert career performance optimization AI. Analyze the user's data to generate 3 actionable, non-generic target missions for next week.
    
    User Context:
    - Career Goal: {user_profile.get('goal')}
    - Application Stage: {user_profile.get('stage')}
    - Current Active Pipeline Jobs: {json.dumps(active_jobs)}
    - Performance Trend Data (Last 4 Records): {json.dumps(performance_logs)}
    - Activity Volume This Week: {session_count} completed sessions (Avg Mood Change: {avg_mood_delta})
    - Completed Targets from Last Week: {prev_completion_count}/3
    
    Requirements:
    1. Focus heavily on pipeline gaps, performance gaps, or momentum drop-offs.
    2. Write highly concrete and contextually tailored strings for this individual user. Avoid generic platitudes.
    3. Return your response exclusively as valid JSON matching the required fields.
    """

    generated_actions = None

    # ----------------==========================
    # STEP 3 & 4 ΓÇö CALL GEMINI WITH STRICT 4S TIMEOUT
    # --------------------------------==========
    try:
        client = genai.Client()

        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiMissionOutput,
                ),
            ),
            timeout=4.0,
        )

        raw_json = json.loads(response.text.strip())

        if (
            raw_json.get("action_1")
            and raw_json.get("action_2")
            and raw_json.get("action_3")
        ):
            generated_actions = raw_json
        else:
            logger.warning(
                "Gemini structure was missing fields. Dropping to fallback handler."
            )
            generated_actions = execute_fallback_generation(context_package)

    except (asyncio.TimeoutError, Exception) as gen_error:
        logger.error(
            f"Gemini generation engine bypassed or timed out: {str(gen_error)}"
        )
        generated_actions = execute_fallback_generation(context_package)

    # ----------------==========================
    # STEP 5 ΓÇö SAVE OR UPDATE SUPABASE RECORD
    # --------------------------------==========
    target_monday = get_target_monday()

    upsert_payload = {
        "user_id": str(user_id),
        "week_start_date": target_monday.isoformat(),
        "action_1": generated_actions["action_1"],
        "action_2": generated_actions["action_2"],
        "action_3": generated_actions["action_3"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    existing_row = (
        supabase.table("weekly_mission")
        .select("*")
        .eq("user_id", user_id)
        .eq("week_start_date", target_monday.isoformat())
        .execute()
    )

    if existing_row.data:
        res = (
            supabase.table("weekly_mission")
            .update(upsert_payload)
            .eq("id", existing_row.data[0]["id"])
            .execute()
        )
    else:
        upsert_payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        upsert_payload["action_1_completed"] = False
        upsert_payload["action_2_completed"] = False
        upsert_payload["action_3_completed"] = False
        upsert_payload["completion_count"] = 0
        res = supabase.table("weekly_mission").insert(upsert_payload).execute()

    # ----------------==========================
    # STEP 6 ΓÇö RETURN MAPPED RESPONSE RECORD
    # --------------------------------==========
    record = res.data[0]

    # Safely handle both standard wire strings and native date/datetime objects from unit test mocks
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
