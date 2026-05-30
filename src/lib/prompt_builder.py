"""Builds the full Gemini prompt by combining system and user prompts."""

from src.lib.emotional_calibration import build_emotional_calibration
from src.prompts.system_prompt import build_system_prompt
from src.prompts.user_prompt import build_user_prompt


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
) -> str:
    """Combine system and user prompts into a single string to send to Gemini."""
    is_mode1 = bool(company and role)

    emotional_calibration = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        anxiety_level_before=anxiety_level_before,
    )

    system = build_system_prompt(
        emotional_calibration=emotional_calibration,
        is_mode1=is_mode1,
    )
    user = build_user_prompt(
        preparation_for=preparation_for,
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        time_available=time_available,
        company=company,
        role=role,
        feeling_note=feeling_note,
        first_name=first_name,
    )

    return f"{system}\n\n{user}"


def derive_preparation_for(
    employment_status: str,
    emotional_challenge: str,
    job_timeline: str,
) -> str:
    """Derive the first session type from onboarding answers."""

    if emotional_challenge in ("rejection_silence", "burnout"):
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

    Based on this, respond ONLY in JSON with no extra text:
    {{
        "phase1": "60-90 seconds of calm breathing...",
        "phase2": "45-60 seconds of grounding...",
        "phase3": "90-120 seconds of visualization tailored to their situation...",
        "phase4": "45-60 seconds acnchoring their capability...",
        "phase5": "30 second confidence send-off specific to this person..."
    }}"""
