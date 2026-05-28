"""Unit tests for fallback template scripts."""
import pytest

from src.lib.fallbacks import get_fallback_script
from src.types.session import SessionScript

ALL_PREPARATION_FOR_VALUES = [
    'interview_tomorrow',
    'recruiter_call',
    'networking',
    'salary_negotiation',
    'rejection_recovery',
    'restarting_search',
    'general_reset',
]

EVENT_SPECIFIC_VALUES = [
    'interview_tomorrow',
    'recruiter_call',
    'networking',
    'salary_negotiation',
]

GENERAL_VALUES = [
    'rejection_recovery',
    'restarting_search',
    'general_reset',
]


@pytest.mark.unit
@pytest.mark.parametrize('preparation_for', ALL_PREPARATION_FOR_VALUES)
def test_all_preparation_for_values_return_a_script(preparation_for: str) -> None:
    """All 7 preparation_for values must return a complete SessionScript with all 5 phases filled."""
    script = get_fallback_script(
        preparation_for=preparation_for,
        company='Acme',
        role='Engineer',
    )
    assert isinstance(script, SessionScript)
    assert script.phase1
    assert script.phase2
    assert script.phase3
    assert script.phase4
    assert script.phase5


@pytest.mark.unit
@pytest.mark.parametrize('preparation_for', EVENT_SPECIFIC_VALUES)
def test_event_specific_templates_contain_company_and_role(preparation_for: str) -> None:
    """Event-specific templates must inject company and role somewhere in the output."""
    company = 'Stripe'
    role = 'Senior Backend Engineer'
    script = get_fallback_script(
        preparation_for=preparation_for,
        company=company,
        role=role,
    )
    full_text = ' '.join([script.phase1, script.phase2, script.phase3, script.phase4, script.phase5])
    assert company in full_text, f'company "{company}" missing from {preparation_for} template'
    assert role in full_text, f'role "{role}" missing from {preparation_for} template'


@pytest.mark.unit
@pytest.mark.parametrize('preparation_for', GENERAL_VALUES)
def test_general_templates_return_script_without_company_and_role(preparation_for: str) -> None:
    """General templates must return a valid script when company and role are not provided."""
    script = get_fallback_script(
        preparation_for=preparation_for,
        company=None,
        role=None,
    )
    assert isinstance(script, SessionScript)
    assert all([script.phase1, script.phase2, script.phase3, script.phase4, script.phase5])


@pytest.mark.unit
@pytest.mark.parametrize('preparation_for', EVENT_SPECIFIC_VALUES)
def test_event_specific_templates_do_not_crash_when_company_and_role_are_none(
    preparation_for: str,
) -> None:
    """Event-specific templates must not crash when company and role are not provided."""
    script = get_fallback_script(
        preparation_for=preparation_for,
        company=None,
        role=None,
    )
    assert isinstance(script, SessionScript)
    assert all([script.phase1, script.phase2, script.phase3, script.phase4, script.phase5])


@pytest.mark.unit
def test_unknown_preparation_for_raises_value_error() -> None:
    """An unrecognised preparation_for value must raise ValueError with a clear message."""
    with pytest.raises(ValueError, match='Unknown preparation_for'):
        get_fallback_script(
            preparation_for='completely_invalid_value',
            company=None,
            role=None,
        )
