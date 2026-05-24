"""Builds the full Gemini prompt by combining system and user prompts."""

from src.lib.emotional_calibration import build_emotional_calibration
from src.prompts.system_prompt import build_system_prompt
from src.prompts.user_prompt import build_user_prompt


def build_prompt(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    pre_score: int,
    company: str | None,
    role: str | None,
    user_context: dict,
) -> str:
    """Combine system and user prompts into a single string to send to Gemini."""
    is_mode1 = bool(company and role)
    baseline_anxiety_level = user_context.get('anxiety_level', 5)

    emotional_calibration = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling=desired_feeling,
        pre_score=pre_score,
        baseline_anxiety_level=baseline_anxiety_level,
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
        user_context=user_context,
    )

    return f"{system}\n\n{user}"
