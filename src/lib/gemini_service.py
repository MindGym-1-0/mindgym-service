"""Gemini Flash integration — tone calibration and session script generation."""
import json

import google.generativeai as genai

from src.lib.config import settings
from src.types.session import SessionScript

_CHIP_TO_PRE_SCORE: dict[str, int] = {
    'overwhelmed': 2,
    'discouraged': 3,
    'exhausted': 3,
    'unsure': 5,
    'anxious but hopeful': 6,
}


def derive_pre_score(current_feeling: str) -> int:
    """Convert a feeling chip string to a pre_score (1–10).

    Raises ValueError for unrecognised chip values.
    """
    key = current_feeling.strip().lower()
    if key not in _CHIP_TO_PRE_SCORE:
        raise ValueError(f'Unknown current_feeling: {current_feeling!r}')
    return _CHIP_TO_PRE_SCORE[key]


def calibrate_tone(pre_score: int) -> str:
    """Map a pre_score to a tone string for the Gemini prompt.

    Raises ValueError if pre_score is outside the valid 1–10 range.
    """
    if not 1 <= pre_score <= 10:
        raise ValueError(f'pre_score out of range: {pre_score}')
    if pre_score <= 3:
        return 'slow and calming'
    if pre_score <= 6:
        return 'balanced and steady'
    return 'confident and energetic'


def generate_script(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    company: str | None,
    role: str | None,
    user_context: dict,
) -> SessionScript | None:
    """Call Gemini Flash and return a SessionScript, or None if the call fails.

    Returns None on timeout, invalid JSON, or failed Mode 1 validation.
    The caller (session_service) is responsible for falling back to a hardcoded template.
    """
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        pre_score = derive_pre_score(current_feeling)

        from src.lib.prompt_builder import build_prompt
        prompt = build_prompt(
            preparation_for=preparation_for,
            current_feeling=current_feeling,
            desired_feeling=desired_feeling,
            time_available=time_available,
            pre_score=pre_score,
            company=company,
            role=role,
            user_context=user_context,
        )

        response = model.generate_content(prompt)
        data = json.loads(response.text)
        script = SessionScript(**data)

        if company and role:
            p3 = script.phase3.lower()
            p5 = script.phase5.lower()
            if (company.lower() not in p3 or role.lower() not in p3
                    or company.lower() not in p5 or role.lower() not in p5):
                return None

        return script

    except Exception:
        return None
