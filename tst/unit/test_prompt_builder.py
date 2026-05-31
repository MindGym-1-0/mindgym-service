"""Unit tests for the prompt builder."""
import pytest
from pydantic import ValidationError

from src.lib.prompt_builder import build_prompt
from src.types.session import SessionStartRequest


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
    )

    assert 'Company:' not in prompt
    assert 'use the actual names' not in prompt


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
    )

    assert 'EMOTIONAL CALIBRATION' in prompt
    assert 'grounding before confidence' in prompt
    assert 'TONE ARC' in prompt


@pytest.mark.unit
def test_feeling_note_appears_in_prompt_when_provided() -> None:
    """feeling_note must appear in the user prompt as extra context for Gemini."""
    prompt = build_prompt(
        preparation_for='interview_tomorrow',
        current_feeling='overwhelmed',
        desired_feeling='confident',
        time_available='10 min',
        anxiety_level_before=2,
        company=None,
        role=None,
        feeling_note='I think I might throw up from nerves',
    )
    assert 'I think I might throw up from nerves' in prompt


@pytest.mark.unit
def test_feeling_note_does_not_change_calibration() -> None:
    """Calibration is driven by the chip (current_feeling), not feeling_note."""
    prompt_without_note = build_prompt(
        preparation_for='general_reset',
        current_feeling='unsure',
        desired_feeling='calm',
        time_available='5 min',
        anxiety_level_before=4,
        company=None,
        role=None,
        feeling_note=None,
    )
    prompt_with_note = build_prompt(
        preparation_for='general_reset',
        current_feeling='unsure',
        desired_feeling='calm',
        time_available='5 min',
        anxiety_level_before=4,
        company=None,
        role=None,
        feeling_note='I have no idea what I am doing',
    )
    assert 'clarity and steady direction' in prompt_without_note
    assert 'clarity and steady direction' in prompt_with_note


@pytest.mark.unit
def test_invalid_current_feeling_rejected_at_request_boundary() -> None:
    """SessionStartRequest must reject an unknown current_feeling with a ValidationError."""
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='a bit nervous',
            desired_feeling='calm',
            time_available='5 min',
            anxiety_level_before=5,
        )
