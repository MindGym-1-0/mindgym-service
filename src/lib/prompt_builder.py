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
    )

    return f"{system}\n\n{user}"
