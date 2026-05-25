"""Unit tests for the Gemini service."""
import pytest

from unittest.mock import MagicMock, patch

from src.lib.gemini_service import calibrate_tone, derive_pre_score, generate_script
from src.types.session import SessionScript


@pytest.mark.unit
@pytest.mark.parametrize('current_feeling,expected_score', [
    ('overwhelmed', 2),
    ('discouraged', 3),
    ('exhausted', 3),
    ('unsure', 5),
    ('anxious but hopeful', 6),
])
def test_derive_pre_score_all_chips(current_feeling: str, expected_score: int) -> None:
    """All 5 feeling chips must map to the correct pre_score."""
    assert derive_pre_score(current_feeling) == expected_score


@pytest.mark.unit
def test_derive_pre_score_unknown_chip_raises_value_error() -> None:
    """An unrecognised chip must raise ValueError."""
    with pytest.raises(ValueError, match='Unknown current_feeling'):
        derive_pre_score('completely_fine')


_VALID_GEMINI_RESPONSE = '{"phase1": "Breathe.", "phase2": "Ground.", "phase3": "Picture yourself at Stripe for your PM role.", "phase4": "Anchor.", "phase5": "You are ready for Stripe as a PM."}'

_USER_CONTEXT = {'goal': 'Land a PM role', 'stage': 'active', 'anxiety_level': 5}


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
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
        )

    assert isinstance(result, SessionScript)
    assert result.phase1 == 'Breathe.'
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
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_when_company_and_role_missing_from_mode1_output() -> None:
    """generate_script must return None when company and role are missing from phase3 or phase5 in Mode 1."""
    mock_response = MagicMock()
    mock_response.text = '{"phase1": "Breathe.", "phase2": "Ground.", "phase3": "Picture yourself at the interview.", "phase4": "Anchor.", "phase5": "You are ready for the role."}'

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
        )

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_when_role_missing_from_mode1_output() -> None:
    """generate_script must return None when role is missing from phase3 or phase5 even if company is present."""
    mock_response = MagicMock()
    mock_response.text = '{"phase1": "Breathe.", "phase2": "Ground.", "phase3": "Picture yourself at Stripe.", "phase4": "Anchor.", "phase5": "You are ready for Stripe."}'

    with patch('src.lib.gemini_service.genai') as mock_genai, \
         patch('src.lib.prompt_builder.build_prompt', return_value='mock prompt'):
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        result = generate_script(
            preparation_for='interview_tomorrow',
            current_feeling='overwhelmed',
            desired_feeling='confident',
            time_available='10 min',
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
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
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
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
            company='Stripe',
            role='PM',
            user_context=_USER_CONTEXT,
        )

    mock_genai.GenerativeModel.assert_called_once_with('gemini-2.0-flash')


@pytest.mark.unit
@pytest.mark.parametrize('pre_score,expected_tone', [
    (1, 'slow and calming'),
    (2, 'slow and calming'),
    (3, 'slow and calming'),
    (4, 'balanced and steady'),
    (5, 'balanced and steady'),
    (6, 'balanced and steady'),
    (7, 'confident and energetic'),
    (8, 'confident and energetic'),
    (9, 'confident and energetic'),
    (10, 'confident and energetic'),
])
def test_tone_calibration_boundary_values(pre_score: int, expected_tone: str) -> None:
    """Tone calibration must return the correct tone for all boundary values."""
    tone = calibrate_tone(pre_score=pre_score)
    assert tone == expected_tone, f'pre_score={pre_score} expected "{expected_tone}" but got "{tone}"'
