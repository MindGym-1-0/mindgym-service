from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.gemini import GeminiServiceError, generate_gemini_flash_json
from src.lib.supabase import get_supabase_user_client
from src.types.coach import (
    ChecklistRequest,
    CoachHomeResponse,
    InterviewChecklistResponse,
    CoachPrepPlanRequest,
    CoachPrepPlanResponse,
    SavedCoachPrepPlanResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_VALID_SESSION_TYPES = {
    "general_reset",
    "interview_tomorrow",
    "recruiter_call",
    "networking",
    "salary_negotiation",
    "rejection_recovery",
    "restarting_search",
}
MAX_SESSION_HISTORY_FOR_PREP = 50
COACH_HOME_CACHE_TTL_SECONDS = 60
_COACH_HOME_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _get_cached_coach_home(user_id: str) -> CoachHomeResponse | None:
    cached = _COACH_HOME_CACHE.get(user_id)
    if not cached:
        return None

    expires_at, payload = cached
    if expires_at <= time.time():
        _COACH_HOME_CACHE.pop(user_id, None)
        return None

    try:
        return CoachHomeResponse.model_validate(payload)
    except Exception:
        _COACH_HOME_CACHE.pop(user_id, None)
        return None


def _set_cached_coach_home(user_id: str, response: CoachHomeResponse) -> None:
    _COACH_HOME_CACHE[user_id] = (
        time.time() + COACH_HOME_CACHE_TTL_SECONDS,
        response.model_dump(),
    )


def _fallback_home_response(has_upcoming_interviews: bool) -> CoachHomeResponse:
    greeting = (
        "You have an upcoming interview soon. Let's steady your energy and keep your prep simple today."
        if has_upcoming_interviews
        else "You're building momentum. Let's keep your routine focused and calm today."
    )
    return CoachHomeResponse(
        recommended_sessions=[
            {
                "title": "Pre-interview calm reset",
                "duration_mins": 10,
                "focus": "Settle your breath and lower stress before important conversations.",
                "session_type": "interview_tomorrow",
            },
            {
                "title": "Confidence builder",
                "duration_mins": 8,
                "focus": "Reinforce strengths and enter conversations with clarity.",
                "session_type": "general_reset",
            },
            {
                "title": "Think clearly under pressure",
                "duration_mins": 12,
                "focus": "Slow down racing thoughts and respond with intention.",
                "session_type": "general_reset",
            },
        ],
        recommended_today=[
            "Short daily sessions tend to improve consistency more than occasional long sessions.",
            "Preparing one specific talking point before practice can reduce interview anxiety.",
            "Mood shifts are often strongest when sessions happen at the same time each day.",
            "A brief reflection after each session helps carry confidence into real interviews.",
        ],
        maya_suggests={
            "text": "Take a short reset session now to build steady momentum for the day.",
            "session_type": "general_reset",
            "time_suggestion": "Try 10 minutes today",
        },
        maya_greeting=greeting,
    )


def _validate_gemini_home_payload(payload: Any) -> CoachHomeResponse | None:
    try:
        model = CoachHomeResponse.model_validate(payload)
    except Exception:
        return None

    if len(model.recommended_sessions) != 3:
        return None
    if len(model.recommended_today) != 4:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in model.recommended_today):
        return None
    if model.maya_suggests.session_type not in _VALID_SESSION_TYPES:
        return None
    for session in model.recommended_sessions:
        if session.session_type not in _VALID_SESSION_TYPES:
            return None
    return model


def _mentions_interview_context(
    text: str, upcoming_interviews: list[dict[str, Any]]
) -> bool:
    lowered_text = (text or "").strip().lower()
    if not lowered_text:
        return False

    for interview in upcoming_interviews:
        company = str(interview.get("company") or "").strip().lower()
        role = str(interview.get("role") or "").strip().lower()

        if company and company in lowered_text:
            return True
        if role and role in lowered_text:
            return True

    return False


def _build_gemini_prompt(
    *,
    user_context: dict[str, Any],
    upcoming_interviews: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    current_streak: int,
) -> str:
    now = datetime.now(timezone.utc)
    interview_lines: list[str] = []
    for idx, interview in enumerate(upcoming_interviews, start=1):
        dt = _parse_iso_datetime(interview.get("interview_date"))
        days_until = (dt.date() - now.date()).days if dt else None
        days_text = f"{days_until} day(s)" if days_until is not None else "unknown days"
        interview_lines.append(
            f"{idx}. company={interview.get('company')}, role={interview.get('role')}, "
            f"interview_date={interview.get('interview_date')}, days_until={days_text}"
        )

    interview_block = (
        "\n".join(interview_lines)
        if interview_lines
        else "No upcoming interviews scheduled"
    )

    sessions_block = (
        "\n".join(
            [
                f"{idx}. preparation_for={s.get('preparation_for')}, mood_delta={s.get('mood_delta')}, completed_at={s.get('completed_at')}"
                for idx, s in enumerate(recent_sessions, start=1)
            ]
        )
        if recent_sessions
        else "No completed ai_sessions yet"
    )

    return (
        "You are Maya, an emotionally intelligent interview coach.\n"
        "Return ONLY valid JSON. No markdown. No backticks. No explanation.\n\n"
        "Create personalized Coach Home content for this user.\n"
        "If upcoming interviews exist, the maya_greeting and maya_suggests.text must reference the upcoming interview context.\n"
        "If no upcoming interviews exist, use a momentum-building tone for general job search support.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "recommended_sessions": [\n'
        '    {"title":"...", "duration_mins":10, "focus":"...", "session_type":"general_reset"}\n'
        "  ],\n"
        '  "recommended_today": ["...", "...", "...", "..."],\n'
        '  "maya_suggests": {"text":"...", "session_type":"general_reset", "time_suggestion":"..."},\n'
        '  "maya_greeting": "..."\n'
        "}\n\n"
        "Hard constraints:\n"
        "- recommended_sessions must contain exactly 3 items.\n"
        "- recommended_today must contain exactly 4 strings.\n"
        "- session_type values must be one of: general_reset, interview_tomorrow, recruiter_call, networking, salary_negotiation, rejection_recovery, restarting_search.\n"
        "- recommendations should use the user's data and recent patterns from ai_sessions.\n\n"
        f"User context:\n"
        f"- goal: {user_context.get('goal')}\n"
        f"- stage: {user_context.get('stage')}\n"
        f"- anxiety_level: {user_context.get('anxiety_level')}\n"
        f"- current_streak: {current_streak}\n\n"
        "Upcoming interviews (next 2):\n"
        f"{interview_block}\n\n"
        "Recent completed ai_sessions (last 5):\n"
        f"{sessions_block}\n"
    )


def _fallback_prep_plan_response(
    *,
    company: str,
    role: str,
    event_type: str,
    worry_input: str,
    days_until: int,
) -> CoachPrepPlanResponse:
    timeline_note = (
        "today" if days_until == 0 else f"in {days_until} day(s)"
    )
    return CoachPrepPlanResponse(
        plan=[
            {
                "day": 1,
                "task": f"Ground your focus for the {company} {role} interview",
                "description": (
                    f"Do a calm reset and name your top 3 concerns about '{worry_input}' so we can turn them into action."
                ),
                "session_type": "general_reset",
                "duration_mins": 10,
            },
            {
                "day": 2,
                "task": f"Practice high-impact stories for the {company} {role} conversation",
                "description": (
                    f"Rehearse concise examples tied to {event_type} expectations and refine one measurable win story."
                ),
                "session_type": "interview_tomorrow",
                "duration_mins": 12,
            },
            {
                "day": 3,
                "task": f"Pressure rehearsal for {company} {role}",
                "description": (
                    "Run a short mock under time pressure and practice slower breathing before each answer."
                ),
                "session_type": "recruiter_call",
                "duration_mins": 10,
            },
            {
                "day": 4,
                "task": f"Confidence and clarity tune-up for {company}",
                "description": (
                    f"Review strengths that match the {role} role, then run one focused session to lower anxiety spikes."
                ),
                "session_type": "general_reset",
                "duration_mins": 8,
            },
            {
                "day": 5,
                "task": f"Final mental prep for your {company} interview",
                "description": (
                    f"Use a brief pre-interview reset and walk in with your top messages clear for {role}, scheduled {timeline_note}."
                ),
                "session_type": "interview_tomorrow",
                "duration_mins": 10,
            },
        ],
        recommended_first_session={
            "session_type": "general_reset",
            "reason": f"Start here to settle worry about '{worry_input}' and create clear thinking before deeper prep.",
            "duration_mins": 10,
        },
        coach_note=(
            f"You're not behind. For your {company} {role} interview, we'll keep this plan focused and realistic. "
            f"We'll use your worry about '{worry_input}' as the signal, practice what matters most, and build confidence step by step."
        ),
    )


def _build_prep_plan_prompt(
    *,
    company: str,
    role: str,
    event_type: str,
    interview_date: str,
    days_until: int,
    goal: str | None,
    stage: str | None,
    anxiety_level: int | None,
    sessions_done_count: int,
    avg_delta: float | None,
    worry_input: str,
) -> str:
    avg_delta_text = "not available" if avg_delta is None else f"{avg_delta:.2f}"
    return (
        "You are Maya, an emotionally intelligent interview coach.\n"
        "Return ONLY valid JSON. No markdown. No backticks. No explanation.\n\n"
        "Build a personalized 5-day prep plan for one interview.\n"
        "The user's worry_input is the PRIMARY signal and must shape the plan.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "plan": [\n'
        '    {"day": 1, "task": "...", "description": "...", "session_type": "general_reset", "duration_mins": 10}\n'
        "  ],\n"
        '  "recommended_first_session": {"session_type": "general_reset", "reason": "...", "duration_mins": 10},\n'
        '  "coach_note": "..."\n'
        "}\n\n"
        "Hard constraints:\n"
        "- plan must contain exactly 5 items.\n"
        "- include both company and role somewhere in the plan text.\n"
        "- each session_type must be one of: general_reset, interview_tomorrow, recruiter_call, networking, salary_negotiation, rejection_recovery, restarting_search.\n"
        "- coach_note must be warm, direct, and personal.\n\n"
        "Interview context:\n"
        f"- company: {company}\n"
        f"- role: {role}\n"
        f"- event_type: {event_type}\n"
        f"- interview_date: {interview_date}\n"
        f"- days_until_interview: {days_until}\n\n"
        "User context:\n"
        f"- goal: {goal}\n"
        f"- stage: {stage}\n"
        f"- anxiety_level: {anxiety_level}\n"
        f"- sessions_done_for_this_interview: {sessions_done_count}\n"
        f"- avg_confidence_boost_mood_delta: {avg_delta_text}\n\n"
        "Primary worry_input:\n"
        f"- {worry_input}\n"
    )


def _validate_gemini_prep_plan_payload(
    payload: Any,
    *,
    company: str,
    role: str,
) -> CoachPrepPlanResponse | None:
    try:
        model = CoachPrepPlanResponse.model_validate(payload)
    except Exception:
        return None

    if len(model.plan) != 5:
        return None
    if not model.coach_note.strip():
        return None
    if model.recommended_first_session.session_type not in _VALID_SESSION_TYPES:
        return None
    for item in model.plan:
        if item.session_type not in _VALID_SESSION_TYPES:
            return None

    combined = " ".join(
        [f"{item.task} {item.description}" for item in model.plan]
    ).lower()
    if company.lower() not in combined or role.lower() not in combined:
        return None

    return model


def _build_checklist_prompt(
    *,
    company: str,
    role: str,
    interview_date: str,
    session_count: int,
    confidence_baseline: float,
    readiness_score: int,
    readiness_label: str,
) -> str:
    return (
        "You are Maya, an empathetic interview mindset coach.\n"
        "Return ONLY valid JSON. No markdown. No backticks. No explanation.\n\n"
        "Generate tonight's focused prep plan as exactly 3 tasks and one motivational quote.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "tonights_plan": [\n'
        '    {"time": "7:00 PM", "task": "..."},\n'
        '    {"time": "8:30 PM", "task": "..."},\n'
        '    {"time": "9:30 PM", "task": "..."}\n'
        "  ],\n"
        '  "quote": "..."\n'
        "}\n\n"
        "Hard constraints:\n"
        "- tonights_plan must contain exactly 3 items.\n"
        "- each tonights_plan item must include non-empty time and task.\n"
        "- quote must be a single non-empty sentence.\n\n"
        "Interview context:\n"
        f"- company: {company}\n"
        f"- role: {role}\n"
        f"- interview_date: {interview_date}\n\n"
        "User prep context:\n"
        f"- completed_sessions_for_this_interview: {session_count}\n"
        f"- confidence_baseline: {confidence_baseline:.2f}/10\n"
        f"- readiness_score: {readiness_score}/10\n"
        f"- readiness_label: {readiness_label}\n"
    )


def _validate_checklist_gemini_payload(payload: Any) -> tuple[list[dict[str, str]], str] | None:
    if not isinstance(payload, dict):
        return None

    tonights_plan = payload.get("tonights_plan")
    quote = payload.get("quote")
    if not isinstance(tonights_plan, list) or len(tonights_plan) != 3:
        return None
    if not isinstance(quote, str) or not quote.strip():
        return None

    validated_plan: list[dict[str, str]] = []
    for item in tonights_plan:
        if not isinstance(item, dict):
            return None
        time_value = str(item.get("time") or "").strip()
        task_value = str(item.get("task") or "").strip()
        if not time_value or not task_value:
            return None
        validated_plan.append({"time": time_value, "task": task_value})

    return validated_plan, quote.strip()


def _fallback_checklist_plan(company: str, role: str) -> tuple[list[dict[str, str]], str]:
    return (
        [
            {
                "time": "7:00 PM",
                "task": f"Review your top stories and examples for the {role} interview at {company}.",
            },
            {
                "time": "8:30 PM",
                "task": "Confirm your interview setup, questions to ask, and opening introduction.",
            },
            {
                "time": "9:30 PM",
                "task": "Do a short breathing reset, then disconnect and rest for tomorrow.",
            },
        ],
        "Preparation compounds confidence. Trust the work you've done and bring calm focus into your interview.",
    )


def _coerce_saved_prep_plan_response(row: dict[str, Any]) -> SavedCoachPrepPlanResponse:
    plan_raw = row.get("plan")
    coach_note = str(row.get("coach_note") or "").strip()
    created_at_raw = row.get("created_at")

    plan_items: list[dict[str, Any]] = []
    recommended_first_session: dict[str, Any] | None = None

    if isinstance(plan_raw, dict):
        nested_plan = plan_raw.get("plan")
        nested_first = plan_raw.get("recommended_first_session")
        if isinstance(nested_plan, list):
            plan_items = nested_plan
        if isinstance(nested_first, dict):
            recommended_first_session = nested_first
    elif isinstance(plan_raw, list):
        plan_items = plan_raw

    if recommended_first_session is None:
        first_type = "general_reset"
        first_duration = 10
        if plan_items and isinstance(plan_items[0], dict):
            first_type = str(plan_items[0].get("session_type") or first_type)
            raw_duration = plan_items[0].get("duration_mins")
            if isinstance(raw_duration, int):
                first_duration = raw_duration
        recommended_first_session = {
            "session_type": first_type,
            "reason": "Start with this session to settle your mind and begin prep with clarity.",
            "duration_mins": first_duration,
        }

    if not isinstance(created_at_raw, str):
        created_at_raw = datetime.now(timezone.utc).isoformat()

    return SavedCoachPrepPlanResponse.model_validate(
        {
            "plan": plan_items,
            "recommended_first_session": recommended_first_session,
            "coach_note": coach_note,
            "created_at": created_at_raw,
        }
    )


@router.post("/checklist", response_model=InterviewChecklistResponse)
async def get_or_create_interview_checklist(
    body: ChecklistRequest,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> InterviewChecklistResponse:
    try:
        sb = get_supabase_user_client(token)
    except Exception:
        logger.exception("Failed to initialize Supabase client for checklist.")
        raise HTTPException(status_code=500, detail="Unable to initialize data client.") from None

    user_id = str(current_user_id)
    interview_id = str(body.interview_id)

    try:
        interview_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("id,company,role,interview_date,job_id")
            .eq("id", interview_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch interview for checklist.")
        raise HTTPException(status_code=500, detail="Unable to fetch interview context.") from None

    interview_rows = interview_res.data or []
    if not interview_rows:
        raise HTTPException(status_code=404, detail="Interview not found.")

    interview = interview_rows[0]
    company = str(interview.get("company") or "your target company").strip()
    role = str(interview.get("role") or "your target role").strip()
    interview_date = str(interview.get("interview_date") or "").strip()
    interview_dt = _parse_iso_datetime(interview_date)
    job_id = interview.get("job_id")

    completed_rows: list[dict[str, Any]] = []
    if job_id:
        try:
            sessions_by_job = await asyncio.to_thread(
                sb.table("ai_sessions")
                .select("id,post_score,completed_at")
                .eq("user_id", user_id)
                .eq("job_id", job_id)
                .not_.is_("completed_at", "null")
                .order("completed_at", desc=True)
                .limit(MAX_SESSION_HISTORY_FOR_PREP)
                .execute
            )
            completed_rows.extend(sessions_by_job.data or [])
        except Exception:
            logger.exception("Checklist ai_sessions job query failed; falling back to company+role query.")

    try:
        sessions_by_company_role = await asyncio.to_thread(
            sb.table("ai_sessions")
            .select("id,post_score,completed_at")
            .eq("user_id", user_id)
            .eq("company", company)
            .eq("role", role)
            .not_.is_("completed_at", "null")
            .order("completed_at", desc=True)
            .limit(MAX_SESSION_HISTORY_FOR_PREP)
            .execute
        )
        completed_rows.extend(sessions_by_company_role.data or [])
    except Exception:
        logger.exception("Checklist ai_sessions company+role query failed.")

    deduped_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in completed_rows:
        row_id = str(row.get("id") or "")
        if row_id and row_id in seen_ids:
            continue
        if row_id:
            seen_ids.add(row_id)
        deduped_rows.append(row)
    completed_rows = deduped_rows

    now = datetime.now(timezone.utc)
    one_day_ago = now.timestamp() - 24 * 60 * 60
    completed_today = False
    completed_last_24h = False
    post_scores: list[float] = []

    for row in completed_rows:
        completed_at = _parse_iso_datetime(str(row.get("completed_at") or ""))
        if completed_at:
            completed_today = completed_today or completed_at.date() == now.date()
            completed_last_24h = completed_last_24h or completed_at.timestamp() >= one_day_ago
        score = row.get("post_score")
        if isinstance(score, (int, float)):
            post_scores.append(float(score))

    session_count = len(completed_rows)
    coaching_checked = session_count >= 5
    breathing_checked = completed_last_24h
    confidence_baseline = sum(post_scores) / len(post_scores) if post_scores else 0.0

    is_tomorrow = interview_dt is not None and interview_dt.date() == (now + timedelta(days=1)).date()
    grounding_checked = completed_today
    grounding_metadata: dict[str, Any] = {}
    if is_tomorrow and not completed_today:
        grounding_metadata = {"recommended_time": "9 PM"}

    mental_prep = [
        {
            "id": "completed_coaching",
            "label": "Completed coaching sessions",
            "checked": coaching_checked,
            "metadata": {"session_count": session_count},
        },
        {
            "id": "breathing_last_night",
            "label": "Breathing session done last night",
            "checked": breathing_checked,
            "metadata": {},
        },
        {
            "id": "grounding_tonight",
            "label": "Final grounding session tonight",
            "checked": grounding_checked,
            "metadata": grounding_metadata,
        },
    ]

    logistics = [
        {"id": "interview_confirmed", "label": "Interview confirmed", "checked": False, "metadata": {}},
        {"id": "questions_prepared", "label": "Questions to ask prepared", "checked": False, "metadata": {}},
        {"id": "quiet_space", "label": "Quiet space confirmed", "checked": False, "metadata": {}},
        {"id": "breathing_session", "label": "Breathing session done last night", "checked": False, "metadata": {}},
    ]

    total_items = 10
    checked_count = (
        sum(1 for item in mental_prep if item["checked"])
        + sum(1 for item in logistics if item["checked"])
    )
    if checked_count >= 8:
        readiness_label = "well prepared"
        readiness_message = (
            f"Looking strong! Only {total_items - checked_count} items remaining to be completely ready."
        )
    elif checked_count >= 5:
        readiness_label = "good progress"
        readiness_message = "Making solid headway. Keep knocking out items on your checklist."
    else:
        readiness_label = "needs attention"
        readiness_message = "Still have a few key target areas left. Let's focus on crossing these off."

    overall_readiness = {
        "score": checked_count,
        "total_items": total_items,
        "label": readiness_label,
        "message": readiness_message,
        "confidence_baseline": round(confidence_baseline, 2),
    }

    prompt = _build_checklist_prompt(
        company=company,
        role=role,
        interview_date=interview_date,
        session_count=session_count,
        confidence_baseline=confidence_baseline,
        readiness_score=checked_count,
        readiness_label=readiness_label,
    )

    tonights_plan, quote = _fallback_checklist_plan(company, role)
    try:
        gemini_payload = await generate_gemini_flash_json(prompt, timeout_seconds=4.0)
        validated = _validate_checklist_gemini_payload(gemini_payload)
        if validated is None:
            logger.warning("Checklist Gemini payload invalid; using fallback tonight plan.")
        else:
            tonights_plan, quote = validated
    except GeminiServiceError:
        logger.exception("Checklist Gemini generation failed; using fallback tonight plan.")

    return InterviewChecklistResponse.model_validate(
        {
            "overall_readiness": overall_readiness,
            "mental_prep": mental_prep,
            "logistics": logistics,
            "tonights_plan": tonights_plan,
            "quote": quote,
        }
    )


@router.get("/home", response_model=CoachHomeResponse)
async def get_coach_home(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> CoachHomeResponse:
    user_id = str(current_user_id)
    cached_response = _get_cached_coach_home(user_id)
    if cached_response is not None:
        return cached_response

    try:
        sb = get_supabase_user_client(token)
    except Exception:
        logger.exception("Failed to initialize Supabase client for coach home; using fallback.")
        response = _fallback_home_response(False)
        _set_cached_coach_home(user_id, response)
        return response

    user_context: dict[str, Any] = {}
    upcoming_interviews: list[dict[str, Any]] = []
    recent_sessions: list[dict[str, Any]] = []
    current_streak = 0

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        users_res = await asyncio.to_thread(
            sb.table("users")
            .select("goal,stage,anxiety_level")
            .eq("id", user_id)
            .limit(1)
            .execute
        )
        user_rows = users_res.data or []
        user_context = user_rows[0] if user_rows else {}

        interviews_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("company,role,interview_date")
            .eq("user_id", user_id)
            .gte("interview_date", now_iso)
            .order("interview_date", desc=False)
            .limit(2)
            .execute
        )
        upcoming_interviews = interviews_res.data or []

        sessions_res = await asyncio.to_thread(
            sb.table("ai_sessions")
            .select("preparation_for,mood_delta,completed_at")
            .eq("user_id", user_id)
            .not_.is_("completed_at", "null")
            .order("completed_at", desc=True)
            .limit(5)
            .execute
        )
        recent_sessions = sessions_res.data or []

        streak_res = await asyncio.to_thread(
            sb.table("streaks")
            .select("current_streak")
            .eq("user_id", user_id)
            .limit(1)
            .execute
        )
        streak_rows = streak_res.data or []
        if streak_rows:
            current_streak = int(streak_rows[0].get("current_streak") or 0)
    except Exception:
        logger.exception("Failed to load coach home data from Supabase; using fallback.")
        response = _fallback_home_response(bool(upcoming_interviews))
        _set_cached_coach_home(user_id, response)
        return response

    prompt = _build_gemini_prompt(
        user_context=user_context,
        upcoming_interviews=upcoming_interviews,
        recent_sessions=recent_sessions,
        current_streak=current_streak,
    )

    try:
        gemini_payload = await generate_gemini_flash_json(prompt, timeout_seconds=4.0)
    except GeminiServiceError:
        logger.exception("Gemini failed for coach home; using fallback.")
        response = _fallback_home_response(bool(upcoming_interviews))
        _set_cached_coach_home(user_id, response)
        return response

    validated = _validate_gemini_home_payload(gemini_payload)
    if validated is None:
        logger.warning("Gemini payload failed CoachHomeResponse validation; using fallback.")
        response = _fallback_home_response(bool(upcoming_interviews))
        _set_cached_coach_home(user_id, response)
        return response
    if upcoming_interviews and not _mentions_interview_context(
        validated.maya_greeting, upcoming_interviews
    ):
        logger.warning(
            "Gemini greeting missed required interview context with upcoming interviews; using fallback."
        )
        response = _fallback_home_response(True)
        _set_cached_coach_home(user_id, response)
        return response

    _set_cached_coach_home(user_id, validated)
    return validated


@router.post("/prep-plan", response_model=CoachPrepPlanResponse)
async def create_coach_prep_plan(
    body: CoachPrepPlanRequest,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> CoachPrepPlanResponse:
    try:
        sb = get_supabase_user_client(token)
    except Exception:
        logger.exception("Failed to initialize Supabase client for prep plan.")
        raise HTTPException(status_code=500, detail="Unable to initialize data client.") from None

    user_id = str(current_user_id)
    interview_id = str(body.interview_id)

    try:
        interview_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("id,company,role,event_type,interview_date,job_id")
            .eq("id", interview_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch interview for prep plan.")
        raise HTTPException(status_code=500, detail="Unable to fetch interview context.") from None

    interview_rows = interview_res.data or []
    if not interview_rows:
        raise HTTPException(status_code=404, detail="Interview not found.")

    interview = interview_rows[0]
    company = str(interview.get("company") or "").strip()
    role = str(interview.get("role") or "").strip()
    event_type = str(interview.get("event_type") or "interview").strip()
    interview_date_raw = str(interview.get("interview_date") or "").strip()
    interview_dt = _parse_iso_datetime(interview_date_raw)
    today = datetime.now(timezone.utc).date()
    days_until = 0
    if interview_dt is not None:
        days_until = max((interview_dt.date() - today).days, 0)
    job_id = interview.get("job_id")

    user_context: dict[str, Any] = {}
    try:
        users_res = await asyncio.to_thread(
            sb.table("users")
            .select("goal,stage,anxiety_level")
            .eq("id", user_id)
            .limit(1)
            .execute
        )
        user_rows = users_res.data or []
        user_context = user_rows[0] if user_rows else {}
    except Exception:
        logger.exception("Failed to fetch user context for prep plan; continuing with defaults.")

    sessions_done_count = 0
    avg_delta: float | None = None
    completed_rows: list[dict[str, Any]] = []

    if job_id:
        try:
            sessions_by_job = await asyncio.to_thread(
                sb.table("ai_sessions")
                .select("mood_delta,completed_at")
                .eq("user_id", user_id)
                .eq("job_id", job_id)
                .not_.is_("completed_at", "null")
                .order("completed_at", desc=True)
                .limit(MAX_SESSION_HISTORY_FOR_PREP)
                .execute
            )
            completed_rows = sessions_by_job.data or []
        except Exception:
            logger.exception(
                "ai_sessions job_id query failed; falling back to company+role matching."
            )

    if not completed_rows:
        try:
            sessions_by_company_role = await asyncio.to_thread(
                sb.table("ai_sessions")
                .select("mood_delta,completed_at")
                .eq("user_id", user_id)
                .eq("company", company)
                .eq("role", role)
                .not_.is_("completed_at", "null")
                .order("completed_at", desc=True)
                .limit(MAX_SESSION_HISTORY_FOR_PREP)
                .execute
            )
            completed_rows = sessions_by_company_role.data or []
        except Exception:
            logger.exception("ai_sessions company+role query failed; proceeding with zero history.")
            completed_rows = []

    sessions_done_count = len(completed_rows)
    deltas: list[float] = []
    for row in completed_rows:
        mood_delta = row.get("mood_delta")
        if isinstance(mood_delta, (int, float)):
            deltas.append(float(mood_delta))
    if deltas:
        avg_delta = sum(deltas) / len(deltas)

    prompt = _build_prep_plan_prompt(
        company=company,
        role=role,
        event_type=event_type,
        interview_date=interview_date_raw,
        days_until=days_until,
        goal=user_context.get("goal"),
        stage=user_context.get("stage"),
        anxiety_level=user_context.get("anxiety_level"),
        sessions_done_count=sessions_done_count,
        avg_delta=avg_delta,
        worry_input=body.worry_input,
    )

    final_response: CoachPrepPlanResponse
    try:
        gemini_payload = await generate_gemini_flash_json(prompt, timeout_seconds=4.0)
        validated = _validate_gemini_prep_plan_payload(
            gemini_payload, company=company, role=role
        )
        if validated is None:
            logger.warning("Gemini prep plan payload failed validation; using fallback.")
            final_response = _fallback_prep_plan_response(
                company=company,
                role=role,
                event_type=event_type,
                worry_input=body.worry_input,
                days_until=days_until,
            )
        else:
            final_response = validated
    except GeminiServiceError:
        logger.exception("Gemini prep plan generation failed; using fallback.")
        final_response = _fallback_prep_plan_response(
            company=company,
            role=role,
            event_type=event_type,
            worry_input=body.worry_input,
            days_until=days_until,
        )

    save_payload = {
        "user_id": user_id,
        "interview_id": interview_id,
        "worry_input": body.worry_input,
        "plan": {
            "plan": [item.model_dump() for item in final_response.plan],
            "recommended_first_session": final_response.recommended_first_session.model_dump(),
        },
        "coach_note": final_response.coach_note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await asyncio.to_thread(
            sb.table("coach_prep_plans")
            .upsert(save_payload, on_conflict="user_id,interview_id")
            .execute
        )
    except Exception:
        logger.exception("Failed to save coach prep plan to Supabase.")
        raise HTTPException(status_code=500, detail="Unable to save prep plan.") from None

    return final_response


@router.get("/prep-plan/{interview_id}", response_model=SavedCoachPrepPlanResponse)
async def get_saved_coach_prep_plan(
    interview_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> SavedCoachPrepPlanResponse:
    try:
        sb = get_supabase_user_client(token)
    except Exception:
        logger.exception("Failed to initialize Supabase client for get prep plan.")
        raise HTTPException(status_code=500, detail="Unable to initialize data client.") from None

    user_id = str(current_user_id)
    interview_id_str = str(interview_id)

    try:
        result = await asyncio.to_thread(
            sb.table("coach_prep_plans")
            .select("plan,coach_note,created_at")
            .eq("user_id", user_id)
            .eq("interview_id", interview_id_str)
            .order("created_at", desc=True)
            .limit(1)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch saved coach prep plan.")
        raise HTTPException(status_code=500, detail="Unable to fetch prep plan.") from None

    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="No saved prep plan found.")

    try:
        return _coerce_saved_prep_plan_response(rows[0])
    except Exception:
        logger.exception("Saved coach prep plan had invalid shape.")
        raise HTTPException(status_code=500, detail="Saved prep plan is invalid.") from None
