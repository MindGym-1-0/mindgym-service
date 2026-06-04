"""OpenAI service — drop-in replacement for gemini_service with the same function signatures."""
from __future__ import annotations

import json
import logging

from openai import OpenAI

from src.lib.config import settings
from src.types.session import SessionScript

logger = logging.getLogger(__name__)


def _client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def _chat(system: str, user: str) -> str | None:
    """Call GPT and return the raw text response, or None on failure."""
    try:
        logger.info("OpenAI system prompt length: %d chars", len(system))
        logger.info("OpenAI user prompt length: %d chars", len(user))
        response = _client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        logger.info("OpenAI raw response: %r", raw[:300] if raw else None)
        return raw
    except Exception as exc:
        logger.exception("OpenAI call failed: %s", exc)
        return None


def generate_script(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    anxiety_level_before: int,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
    user_context: dict | None = None,
) -> SessionScript | None:
    """Call GPT and return a SessionScript, or None if the call fails."""
    from src.lib.prompt_builder import build_prompt_parts
    from src.lib.gemini_service import is_hype_in_phase1

    system, user = build_prompt_parts(
        preparation_for=preparation_for,
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        time_available=time_available,
        anxiety_level_before=anxiety_level_before,
        company=company,
        role=role,
        feeling_note=feeling_note,
        user_context=user_context,
    )

    raw = _chat(system, user)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        script = SessionScript(**data)
    except Exception as exc:
        logger.exception("Failed to parse OpenAI session script: %s", exc)
        return None

    if company and role:
        p3 = script.phase3.lower()
        p5 = script.phase5.lower()
        if (
            company.lower() not in p3
            or role.lower() not in p3
            or company.lower() not in p5
            or role.lower() not in p5
        ):
            logger.warning(
                "Mode 1 validation failed — company=%r role=%r missing from phase3/phase5",
                company, role,
            )
            return None

    if anxiety_level_before >= 7 and is_hype_in_phase1(script.phase1):
        logger.warning("Hype guard triggered — phase1 contains hype at anxiety=%d", anxiety_level_before)
        return None

    return script


def analyze_onboarding(
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
    preparation_for: str | None = None,
) -> dict | None:
    """Analyze onboarding answers and return gap analysis dict, or None on failure."""
    from src.lib.prompt_builder import build_onboarding_prompt

    prompt = build_onboarding_prompt(
        employment_status=employment_status,
        unemployed_duration=unemployed_duration,
        job_timeline=job_timeline,
        target_role_category=target_role_category,
        target_role_note=target_role_note,
        company_types=company_types,
        applications_sent_min=applications_sent_min,
        applications_sent_max=applications_sent_max,
        recruiter_contacts=recruiter_contacts,
        first_round_interviews=first_round_interviews,
        final_round_interviews=final_round_interviews,
        offers=offers,
        emotional_challenge=emotional_challenge,
        baseline_anxiety=baseline_anxiety,
        preparation_for=preparation_for,
    )

    raw = _chat("You are Maya, a mental performance coach. Return ONLY valid JSON, no markdown.", prompt)
    if raw is None:
        return None

    try:
        return json.loads(raw)
    except Exception as exc:
        logger.exception("Failed to parse OpenAI gap analysis: %s", exc)
        return None


def generate_onboarding_script(
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
    preparation_for: str | None = None,
) -> SessionScript | None:
    """Generate the first session script from onboarding data, or None on failure.

    Uses the same prompt pipeline as regular sessions (build_prompt_parts) so
    the first session gets identical quality to every session after it.
    Onboarding fields are passed as user_context to populate the about_block.
    Session inputs are derived from onboarding data — no user input needed.
    """
    from src.lib.prompt_builder import build_prompt_parts, derive_preparation_for

    anxiety = baseline_anxiety or 5

    _challenge_to_feeling = {
        "rejection_silence": "discouraged",
        "interview_anxiety": "anxious but hopeful",
        "imposter_syndrome": "unsure",
        "burnout": "exhausted",
        "uncertainty": "unsure",
        "financial_pressure": "overwhelmed",
    }
    current_feeling = _challenge_to_feeling.get(emotional_challenge or "", "unsure")

    derived_preparation_for = preparation_for or derive_preparation_for(
        employment_status=employment_status,
        emotional_challenge=emotional_challenge or "",
        job_timeline=job_timeline,
    )

    user_context = {
        "employment_status": employment_status,
        "unemployed_duration": unemployed_duration,
        "job_timeline": job_timeline,
        "target_role_category": target_role_category,
        "target_role_note": target_role_note,
        "company_types": company_types,
        "applications_sent_min": applications_sent_min,
        "applications_sent_max": applications_sent_max,
        "recruiter_contacts": recruiter_contacts,
        "first_round_interviews": first_round_interviews,
        "final_round_interviews": final_round_interviews,
        "offers": offers,
        "emotional_challenge": emotional_challenge,
        "baseline_anxiety": baseline_anxiety,
    }

    system, user = build_prompt_parts(
        preparation_for=derived_preparation_for,
        current_feeling=current_feeling,
        desired_feeling="grounded",
        time_available="10 min",
        anxiety_level_before=anxiety,
        company=None,
        role=None,
        user_context=user_context,
    )

    raw = _chat(system, user)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        return SessionScript(**data)
    except Exception as exc:
        logger.exception("Failed to parse OpenAI onboarding script: %s", exc)
        return None
