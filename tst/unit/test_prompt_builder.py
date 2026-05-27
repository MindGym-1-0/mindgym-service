"""Unit tests for the prompt builder."""
import pytest

from src.lib.prompt_builder import build_prompt


_USER_CONTEXT = {'goal': 'Land a PM role', 'stage': 'active'}
_USER_CONTEXT_WITH_NAME = {**_USER_CONTEXT, 'first_name': 'Claire'}


@pytest.mark.unit
def test_build_prompt_mode1_contains_company_and_role() -> None:
    """Mode 1 prompt must include company and role in both system and user sections."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company='Stripe',
        role='PM',
        user_context=_USER_CONTEXT,
    )

    assert 'Stripe' in prompt
    assert 'PM' in prompt


@pytest.mark.unit
def test_build_prompt_mode1_contains_critical_rules() -> None:
    """Mode 1 prompt must include the critical rules block demanding explicit company/role names."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company='Stripe',
        role='PM',
        user_context=_USER_CONTEXT,
    )

    assert 'CRITICAL' in prompt


@pytest.mark.unit
def test_build_prompt_mode2_omits_company_and_role_sections() -> None:
    """Mode 2 prompt must not include company/role context or mode1 company enforcement."""
    prompt = build_prompt(
        preparation_for='networking_event',
        current_feeling='unsure',
        desired_feeling='calm',
        time_available='5 min',
        anxiety_level_before=5,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'Company:' not in prompt
    assert 'use the actual names' not in prompt


@pytest.mark.unit
def test_build_prompt_contains_user_context_fields() -> None:
    """Prompt must include the user context fields: goal and stage."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'Land a PM role' in prompt
    assert 'active' in prompt
    assert '2' in prompt


@pytest.mark.unit
def test_build_prompt_contains_session_inputs() -> None:
    """Prompt must include all session inputs from the user."""
    prompt = build_prompt(
        preparation_for='salary_negotiation',
        current_feeling='anxious but hopeful',
        desired_feeling='calm',
        time_available='15 min',
        anxiety_level_before=6,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'salary_negotiation' in prompt
    assert 'anxious but hopeful' in prompt
    assert 'calm' in prompt
    assert '15 min' in prompt


@pytest.mark.unit
def test_build_prompt_contains_maya_persona() -> None:
    """Prompt must include Maya's persona from the system prompt."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'Maya' in prompt


@pytest.mark.unit
def test_build_prompt_contains_phase_structure() -> None:
    """Prompt must include phase length guidance."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'phase1' in prompt
    assert 'phase5' in prompt


@pytest.mark.unit
def test_build_prompt_contains_json_output_instruction() -> None:
    """Prompt must instruct Gemini to return strict JSON only."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'JSON' in prompt


@pytest.mark.unit
def test_build_prompt_contains_emotional_calibration() -> None:
    """Prompt must include emotional calibration fields in the system prompt."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT,
    )

    assert 'EMOTIONAL CALIBRATION' in prompt
    assert 'grounding before confidence' in prompt
    assert 'TONE ARC' in prompt


@pytest.mark.unit
def test_build_prompt_includes_first_name_when_provided() -> None:
    """Prompt must include the user's first name when present in user_context."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        user_context=_USER_CONTEXT_WITH_NAME,
    )

    assert 'Claire' in prompt
