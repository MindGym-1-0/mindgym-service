"""Builds the full Gemini prompt by combining system and user prompts."""

from src.lib.emotional_calibration import build_emotional_calibration
from src.prompts.system_prompt import build_system_prompt
from src.prompts.user_prompt import build_user_prompt


def build_prompt_parts(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    anxiety_level_before: int,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
    first_name: str | None = None,
    user_context: dict | None = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) as separate strings.

    Used by OpenAI service which expects system/user roles separately.
    """
    is_event_linked = bool(company and role)

    emotional_calibration = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        anxiety_level_before=anxiety_level_before,
    )

    system = build_system_prompt(is_event_linked=is_event_linked)
    user = build_user_prompt(
        preparation_for=preparation_for,
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        time_available=time_available,
        company=company,
        role=role,
        feeling_note=feeling_note,
        first_name=first_name,
        user_context=user_context,
        anxiety_level_before=anxiety_level_before,
        emotional_calibration=emotional_calibration,
    )

    return system, user


def build_prompt(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    anxiety_level_before: int,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
    first_name: str | None = None,
    user_context: dict | None = None,
) -> str:
    """Combine system and user prompts into a single string to send to Gemini."""
    is_event_linked = bool(company and role)

    emotional_calibration = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        anxiety_level_before=anxiety_level_before,
    )

    system = build_system_prompt(is_event_linked=is_event_linked)
    user = build_user_prompt(
        preparation_for=preparation_for,
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        time_available=time_available,
        company=company,
        role=role,
        feeling_note=feeling_note,
        first_name=first_name,
        user_context=user_context,
        anxiety_level_before=anxiety_level_before,
        emotional_calibration=emotional_calibration,
    )

    return f"{system}\n\n{user}"


def derive_preparation_for(
    employment_status: str,
    emotional_challenge: list[str],
    job_timeline: str,
) -> str:
    """Derive the first session type from onboarding answers."""

    if any(c in ("rejection_silence", "burnout") for c in emotional_challenge):
        return "rejection_recovery"
    elif employment_status == "employed":
        return "general_reset"
    elif job_timeline == "asap":
        return "restarting_search"
    else:
        return "general_reset"


def build_onboarding_prompt(
    employment_status: str,
    unemployed_duration: str,
    job_timeline: str,
    target_role_category: str,
    target_role_note: str | None = None,
    company_types: list[str] | None = None,
    applications_sent_min: int | None = None,
    applications_sent_max: int | None = None,
    recruiter_contacts: int | None = None,
    first_round_interviews: int | None = None,
    final_round_interviews: int | None = None,
    offers: int | None = None,
    emotional_challenge: str | None = None,
    baseline_anxiety: int | None = None,
    preparation_for: str | None = None
) -> str:
    """Build the prompt for onboarding analysis."""
    return f"""You are Maya, a mental performance coach for job seekers.

    A new user just completed onboarding. Here are their answers:

    - First session type: {preparation_for}
    - Employment status: {employment_status}
    - How long searching: {unemployed_duration or 'N/A (currently employed)'}
    - Job timeline: {job_timeline}
    - Target role: {target_role_category}{f' — {target_role_note}' if target_role_note else ''}
    - Company types: {company_types}
    - Applications sent: {applications_sent_min}–{applications_sent_max}
    - Recruiter contacts: {recruiter_contacts}
    - First round interviews: {first_round_interviews}
    - Final round interviews: {final_round_interviews}
    - Offers: {offers}
    - Hardest part emotionally: {emotional_challenge}
    - Baseline anxiety: {baseline_anxiety}/10

    Based on this, respond ONLY in JSON with no extra text:
    {{
        "session_title": "title for the first session card",
        "session_description": "2 sentences describing the session",
        "session_tags": ["tag1", "tag2", "tag3"],
        "mindset_gap": "short label",
        "mindset_gap_detail": "one sentence",
        "hunting_gap": "short label or null",
        "hunting_gap_detail": "one sentence or null",
        "baseline_anxiety_note": "short note about what Maya will do with this score"
    }}"""


def build_onboarding_script_prompt(
    employment_status: str,
    unemployed_duration: str,
    job_timeline: str,
    target_role_category: str,
    target_role_note: str | None = None,
    company_types: list[str] | None = None,
    applications_sent_min: int | None = None,
    applications_sent_max: int | None = None,
    recruiter_contacts: int | None = None,
    first_round_interviews: int | None = None,
    final_round_interviews: int | None = None,
    offers: int | None = None,
    emotional_challenge: str | None = None,
    baseline_anxiety: int | None = None,
    preparation_for: str | None = None
) -> str:
    """Build the prompt for onboarding session script."""
    return f"""You are Maya, a mental performance coach for job seekers.

    A new user just completed onboarding. Here are their answers:

    - First session type: {preparation_for}
    - Employment status: {employment_status}
    - How long searching: {unemployed_duration or 'N/A (currently employed)'}
    - Job timeline: {job_timeline}
    - Target role: {target_role_category}{f' — {target_role_note}' if target_role_note else ''}
    - Company types: {company_types}
    - Applications sent: {applications_sent_min}–{applications_sent_max}
    - Recruiter contacts: {recruiter_contacts}
    - First round interviews: {first_round_interviews}
    - Final round interviews: {final_round_interviews}
    - Offers: {offers}
    - Hardest part emotionally: {emotional_challenge}
    - Baseline anxiety: {baseline_anxiety}/10

    Generate their first personalised mental health session.

    Write their first personalised 5-phase mental performance session. Follow the phase rules exactly: phase1 is calm breathing (60-90s), phase2 is present-moment grounding (45-60s), phase3 is vivid visualization anchored to ONE specific picturable moment (90-120s), phase4 anchors a DIFFERENT past event showing underlying capability (45-60s), phase5 is a short punchy send-off naming a concrete next step (30s).

    Respond ONLY in JSON with no extra text:
    {{
        "phase1": "...",
        "phase2": "...",
        "phase3": "...",
        "phase4": "...",
        "phase5": "..."
    }}"""
