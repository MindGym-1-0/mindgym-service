"""Gemini Flash integration — tone calibration and session script generation."""
import json

import google.generativeai as genai

from src.lib.config import settings
from src.types.session import SessionScript


# Heuristic smoke-alarm — deliberately crude word list.
# Fires ONLY at anxiety_level_before >= 7 to catch the worst-case failure:
# amping up someone who needs grounding. This is not a real tone check.
# Semantic tone and acknowledgment validation is a future LLM-judge task.
_HIGH_ANXIETY_HYPE_WORDS = frozenset({
    'pump', 'pumped', 'energy', 'energized', 'excited', 'hyped',
    "let's go", 'crush it', 'fired up', 'unstoppable',
})


def is_hype_in_phase1(phase1: str) -> bool:
    """Return True if phase1 contains energizing/hype language."""
    text = phase1.lower()
    return any(word in text for word in _HIGH_ANXIETY_HYPE_WORDS)


def calibrate_tone(anxiety_level_before: int) -> str:
    """Map an anxiety_level_before score to a tone string for the Gemini prompt.

    Scale: 1 = calm/not anxious, 10 = extremely anxious.
    High anxiety → grounding tone; low anxiety → affirming/priming tone.
    Raises ValueError if the score is outside the valid 1–10 range.
    """
    if not 1 <= anxiety_level_before <= 10:
        raise ValueError(f'anxiety_level_before out of range: {anxiety_level_before}')
    if anxiety_level_before <= 3:
        return 'affirming, peak-performance priming'
    if anxiety_level_before <= 6:
        return 'steady and focusing; normalize the nerves'
    return 'slow, grounding, present-tense regulation'


def generate_script(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    anxiety_level_before: int,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
) -> SessionScript | None:
    """Call Gemini Flash and return a SessionScript, or None if the call fails.

    Returns None on timeout, invalid JSON, or failed Mode 1 validation.
    The caller (session_service) is responsible for falling back to a hardcoded template.
    """
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        from src.lib.prompt_builder import build_prompt
        prompt = build_prompt(
            preparation_for=preparation_for,
            current_feeling=current_feeling,
            desired_feeling=desired_feeling,
            time_available=time_available,
            anxiety_level_before=anxiety_level_before,
            company=company,
            role=role,
            feeling_note=feeling_note,
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=600),
        )
        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(raw)
        script = SessionScript(**data)

        if company and role:
            p3 = script.phase3.lower()
            p5 = script.phase5.lower()
            if (company.lower() not in p3 or role.lower() not in p3
                    or company.lower() not in p5 or role.lower() not in p5):
                return None

        if anxiety_level_before >= 7 and is_hype_in_phase1(script.phase1):
            return None

        return script

    except Exception:
        return None


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
    preparation_for: str | None = None
) -> dict | None:
    """Analyze onboarding answers and decide the first session.

    Sends all user answers to Gemini and returns a dict with:
    - preparation_for: which session type to run first
    - session_title: title shown on the summary card
    - session_description: 2-sentence description for the card
    - session_tags: chip labels for the card
    - mindset_gap: label for the mindset gap
    - mindset_gap_detail: one sentence detail
    - hunting_gap: label for the hunting gap (or None)
    - hunting_gap_detail: one sentence detail (or None)
    - baseline_anxiety_note: what Maya will do with the score

    Returns None if Gemini fails.
    """
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

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
            preparation_for=preparation_for
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=600),
        )

        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(raw)
        return data

    except Exception:
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
    preparation_for: str | None = None
) -> SessionScript | None:
    """Call Gemini Flash and return a SessionScript, or None if the call fails.

    Returns None on timeout, invalid JSON.
    """
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        from src.lib.prompt_builder import build_onboarding_script_prompt
        prompt = build_onboarding_script_prompt(
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
            preparation_for=preparation_for
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=600),
        )

        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        data = json.loads(raw)
        script = SessionScript(**data)

        return script

    except Exception:
        return None
