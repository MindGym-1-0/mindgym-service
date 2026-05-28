"""Unit tests for the Gemini service."""
import pytest

from unittest.mock import MagicMock, patch

from src.lib.gemini_service import calibrate_tone, generate_script, is_hype_in_phase1
from src.types.session import SessionScript


_VALID_GEMINI_RESPONSE = (
    '{"phase1": "Close your eyes and take a slow breath in.",'
    ' "phase2": "Feel the ground beneath you, steady and real.",'
    ' "phase3": "Picture yourself at Stripe for your PM role.",'
    ' "phase4": "Recall a time you performed under pressure and delivered.",'
    ' "phase5": "You are ready for Stripe as a PM today."}'
)


@pytest.mark.unit
def test_generate_script_returns_session_script_on_success() -> None:
    """generate_script must return a SessionScript when Gemini returns valid JSON."""
    mock_response = MagicMock()
    mock_response.text = _VALID_GEMINI_RESPONSE

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    assert isinstance(result, SessionScript)
    assert result.phase1 == 'Close your eyes and take a slow breath in.'
    assert result.phase3 == 'Picture yourself at Stripe for your PM role.'


@pytest.mark.unit
def test_generate_script_returns_none_on_timeout() -> None:
    """generate_script must return None when Gemini times out."""
    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = TimeoutError
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_when_company_and_role_missing_from_mode1_output() -> None:
    """generate_script must return None when company and role are missing from phase3 or phase5 in Mode 1."""
    mock_response = MagicMock()
    mock_response.text = '{"phase1": "Close your eyes and breathe slowly.", "phase2": "Feel the ground beneath you, steady and real.", "phase3": "Picture yourself at the interview room.", "phase4": "Recall a moment when you performed well.", "phase5": "You are ready for the role today."}'

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_when_role_missing_from_mode1_output() -> None:
    """generate_script must return None when role is missing from phase3 or phase5 even if company is present."""
    mock_response = MagicMock()
    mock_response.text = '{"phase1": "Close your eyes and breathe slowly.", "phase2": "Feel the ground beneath you, steady and real.", "phase3": "Picture yourself walking into Stripe today.", "phase4": "Recall a moment when you performed well.", "phase5": "You are ready for Stripe and this moment."}'

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_on_invalid_json() -> None:
    """generate_script must return None when Gemini returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.text = 'this is not json at all'

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_uses_configured_model_name() -> None:
    """generate_script must pass the model name from settings to GenerativeModel."""
    mock_response = MagicMock()
    mock_response.text = _VALID_GEMINI_RESPONSE

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.gemini_service.settings') as mock_settings, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_settings.gemini_api_key = 'test-key'
        mock_settings.gemini_model = 'gemini-2.0-flash'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response

        generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=2,
            company='Stripe',
            role='PM',
        )

    mock_genai.GenerativeModel.assert_called_once_with('gemini-2.0-flash')


@pytest.mark.unit
@pytest.mark.parametrize('anxiety_level_before,expected_tone', [
    (1, 'affirming, peak-performance priming'),
    (2, 'affirming, peak-performance priming'),
    (3, 'affirming, peak-performance priming'),
    (4, 'steady and focusing; normalize the nerves'),
    (5, 'steady and focusing; normalize the nerves'),
    (6, 'steady and focusing; normalize the nerves'),
    (7, 'slow, grounding, present-tense regulation'),
    (8, 'slow, grounding, present-tense regulation'),
    (9, 'slow, grounding, present-tense regulation'),
    (10, 'slow, grounding, present-tense regulation'),
])
def test_tone_calibration_boundary_values(anxiety_level_before: int, expected_tone: str) -> None:
    """Tone calibration must return the correct tone for all boundary values."""
    tone = calibrate_tone(anxiety_level_before=anxiety_level_before)
    assert tone == expected_tone, f'anxiety_level_before={anxiety_level_before} expected "{expected_tone}" but got "{tone}"'


# --- is_hype_in_phase1 ---

@pytest.mark.unit
@pytest.mark.parametrize('phase1', [
    'Let\'s go — you are pumped and ready for this.',
    'You are fired up and unstoppable today.',
    'Feel the energy building inside you right now.',
    'You are hyped and crush it today.',
    'You are energized and excited for what comes next.',
])
def test_is_hype_in_phase1_detects_hype_language(phase1: str) -> None:
    """is_hype_in_phase1 must return True when phase1 contains energizing/hype words."""
    assert is_hype_in_phase1(phase1) is True


@pytest.mark.unit
@pytest.mark.parametrize('phase1', [
    'Close your eyes and take a slow, steady breath.',
    'Notice your feet on the floor and soften your shoulders.',
    'You are here, present, and that is enough right now.',
    'Breathe in slowly and let your body settle into this moment.',
])
def test_is_hype_in_phase1_passes_calm_language(phase1: str) -> None:
    """is_hype_in_phase1 must return False when phase1 contains calm/grounding language."""
    assert is_hype_in_phase1(phase1) is False


# --- generate_script hype guard ---

_HYPE_PHASE1_RESPONSE = (
    '{"phase1": "Let\'s go — you are fired up and ready for this interview.",'
    ' "phase2": "Feel the ground beneath you, steady and real.",'
    ' "phase3": "Picture yourself at Stripe for your PM role.",'
    ' "phase4": "Recall a time you performed under pressure and delivered.",'
    ' "phase5": "You are ready for Stripe as a PM today."}'
)

_CALM_PHASE1_RESPONSE = (
    '{"phase1": "Close your eyes and take a slow, steady breath in.",'
    ' "phase2": "Feel the ground beneath you, steady and real.",'
    ' "phase3": "Picture yourself at Stripe for your PM role.",'
    ' "phase4": "Recall a time you performed under pressure and delivered.",'
    ' "phase5": "You are ready for Stripe as a PM today."}'
)


@pytest.mark.unit
def test_generate_script_returns_none_when_high_anxiety_and_hype_in_phase1() -> None:
    """generate_script must return None when anxiety >= 7 and phase1 contains hype language."""
    mock_response = MagicMock()
    mock_response.text = _HYPE_PHASE1_RESPONSE

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=7,
            company='Stripe',
            role='PM',
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_passes_when_high_anxiety_and_calm_phase1() -> None:
    """generate_script must return a SessionScript when anxiety >= 7 but phase1 is calm."""
    mock_response = MagicMock()
    mock_response.text = _CALM_PHASE1_RESPONSE

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=7,
            company='Stripe',
            role='PM',
        )

    assert isinstance(result, SessionScript)


@pytest.mark.unit
def test_generate_script_passes_when_low_anxiety_and_hype_in_phase1() -> None:
    """generate_script must not reject hype language in phase1 when anxiety < 7."""
    mock_response = MagicMock()
    mock_response.text = _HYPE_PHASE1_RESPONSE

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            anxiety_level_before=6,
            company='Stripe',
            role='PM',
        )

    assert isinstance(result, SessionScript)
