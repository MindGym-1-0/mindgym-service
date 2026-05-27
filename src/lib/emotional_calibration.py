"""Derives emotional calibration from session inputs for prompt construction."""

from src.lib.gemini_service import calibrate_tone

# anxiety_level_before bands → stress / energy / confidence
_INTENSITY_BANDS: dict[str, tuple[str, str, str]] = {
    'low':      ('high',     'low',    'low'),
    'moderate': ('moderate', 'moderate', 'moderate'),
    'high':     ('low',      'high',   'high'),
}

def _intensity_band(anxiety_level_before: int) -> str:
    if anxiety_level_before <= 3:
        return 'low'
    if anxiety_level_before <= 6:
        return 'moderate'
    return 'high'


# current_feeling → primary_need + tone_arc (phase1–4; phase5 is overridden by desired_feeling)
_FEELING_ARCS: dict[str, dict] = {
    'overwhelmed': {
        'primary_need': 'grounding before confidence',
        'tone_arc': {
            'phase1': 'very slow, calming, body-first',
            'phase2': 'stabilizing and reassuring',
            'phase3': 'steady visualization, no hype',
            'phase4': 'warm evidence-based confidence',
        },
    },
    'discouraged': {
        'primary_need': 'restore belief and self-worth',
        'tone_arc': {
            'phase1': 'gentle validation, not overly clinical',
            'phase2': 'grounded reassurance',
            'phase3': 'reconnect the user to possibility',
            'phase4': 'evidence from past resilience',
        },
    },
    'exhausted': {
        'primary_need': 'low-effort recovery and gentle readiness',
        'tone_arc': {
            'phase1': 'restful, slow, permission to soften',
            'phase2': 'body relaxation and reduced pressure',
            'phase3': 'simple visualization with low cognitive load',
            'phase4': 'remind them capability does not require force',
        },
    },
    'unsure': {
        'primary_need': 'clarity and steady direction',
        'tone_arc': {
            'phase1': 'settling and slowing mental noise',
            'phase2': 'grounding into what is known',
            'phase3': 'clear, specific rehearsal',
            'phase4': 'identity-based reassurance',
        },
    },
    'anxious but hopeful': {
        'primary_need': 'channel nervous energy into confidence',
        'tone_arc': {
            'phase1': 'steady breath, not too slow',
            'phase2': 'grounding with momentum',
            'phase3': 'confident, vivid rehearsal',
            'phase4': 'activate proof of capability',
        },
    },
}

# desired_feeling → phase5 landing
_PHASE5_LANDINGS: dict[str, str] = {
    'calm':        'softer ending',
    'grounded':    'steady ending',
    'confident':   'stronger send-off',
    'focused':     'clear next-step ending',
    'clear_minded': 'uncluttered, simple ending',
    'composed':    'poised, controlled ending',
}

_PHASE5_DEFAULT = 'concise confidence boost'


def build_emotional_calibration(
    current_feeling: str,
    desired_feeling: str,
    anxiety_level_before: int,
    baseline_anxiety_level: int,
) -> dict:
    """Build an emotional calibration object from session inputs.

    Combines anxiety_level_before intensity, current_feeling shape, and desired_feeling
    destination into a structured object for the system prompt.

    Raises ValueError for unrecognised current_feeling values.
    """
    if not 1 <= anxiety_level_before <= 10:
        raise ValueError(f'anxiety_level_before out of range: {anxiety_level_before}. Must be 1–10.')

    key = current_feeling.strip().lower()
    if key not in _FEELING_ARCS:
        raise ValueError(f'Unknown current_feeling: {current_feeling!r}')

    band = _intensity_band(anxiety_level_before)
    stress_level, energy_level, confidence_level = _INTENSITY_BANDS[band]

    arc_def = _FEELING_ARCS[key]
    tone_arc = {**arc_def['tone_arc']}
    tone_arc['phase5'] = _PHASE5_LANDINGS.get(desired_feeling.strip().lower(), _PHASE5_DEFAULT)

    return {
        'current_feeling': current_feeling,
        'desired_feeling': desired_feeling,
        'anxiety_level_before': anxiety_level_before,
        'baseline_anxiety_level': baseline_anxiety_level,
        'stress_level': stress_level,
        'energy_level': energy_level,
        'confidence_level': confidence_level,
        'primary_need': arc_def['primary_need'],
        'tone': calibrate_tone(anxiety_level_before),
        'tone_arc': tone_arc,
    }
