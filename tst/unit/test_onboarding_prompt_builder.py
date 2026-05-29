"""Unit tests for onboarding prompt builder functions."""
import pytest
from src.lib.prompt_builder import derive_preparation_for, build_onboarding_prompt, build_onboarding_script_prompt


# ---------------------------------------------------------------------------
# derive_preparation_for
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_rejection_silence_returns_rejection_recovery() -> None:
    result = derive_preparation_for(
        employment_status="unemployed",
        emotional_challenge="rejection_silence",
        job_timeline="3m",
    )
    assert result == "rejection_recovery"


@pytest.mark.unit
def test_burnout_returns_rejection_recovery() -> None:
    result = derive_preparation_for(
        employment_status="unemployed",
        emotional_challenge="burnout",
        job_timeline="3m",
    )
    assert result == "rejection_recovery"


@pytest.mark.unit
def test_employed_returns_general_reset() -> None:
    result = derive_preparation_for(
        employment_status="employed",
        emotional_challenge="interview_anxiety",
        job_timeline="6m",
    )
    assert result == "general_reset"


@pytest.mark.unit
def test_asap_timeline_returns_restarting_search() -> None:
    result = derive_preparation_for(
        employment_status="unemployed",
        emotional_challenge="interview_anxiety",
        job_timeline="asap",
    )
    assert result == "restarting_search"


@pytest.mark.unit
def test_fallback_returns_general_reset() -> None:
    result = derive_preparation_for(
        employment_status="unemployed",
        emotional_challenge="uncertainty",
        job_timeline="12m",
    )
    assert result == "general_reset"


@pytest.mark.unit
def test_emotional_challenge_takes_priority_over_timeline() -> None:
    """rejection_silence should win over asap timeline."""
    result = derive_preparation_for(
        employment_status="unemployed",
        emotional_challenge="rejection_silence",
        job_timeline="asap",
    )
    assert result == "rejection_recovery"


# ---------------------------------------------------------------------------
# build_onboarding_prompt — smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_onboarding_prompt_returns_string() -> None:
    result = build_onboarding_prompt(
        employment_status="unemployed",
        unemployed_duration="3m",
        job_timeline="asap",
        target_role_category="product_management",
        target_role_note="Senior PM",
        company_types=["startup"],
        applications_sent_min=10,
        applications_sent_max=15,
        recruiter_contacts=3,
        first_round_interviews=2,
        final_round_interviews=1,
        offers=0,
        emotional_challenge="rejection_silence",
        baseline_anxiety=7,
        preparation_for="rejection_recovery",
    )
    assert isinstance(result, str)
    assert len(result) > 100


@pytest.mark.unit
def test_build_onboarding_prompt_includes_user_answers() -> None:
    result = build_onboarding_prompt(
        employment_status="employed",
        unemployed_duration=None,
        job_timeline="6m",
        target_role_category="software_engineering",
        target_role_note=None,
        company_types=["large_tech"],
        applications_sent_min=5,
        applications_sent_max=10,
        recruiter_contacts=2,
        first_round_interviews=1,
        final_round_interviews=0,
        offers=0,
        emotional_challenge="imposter_syndrome",
        baseline_anxiety=5,
        preparation_for="general_reset",
    )
    assert "employed" in result
    assert "software_engineering" in result
    assert "imposter_syndrome" in result
    assert "5/10" in result


@pytest.mark.unit
def test_build_onboarding_prompt_handles_none_duration() -> None:
    result = build_onboarding_prompt(
        employment_status="employed",
        unemployed_duration=None,
        job_timeline="12m",
        target_role_category="marketing",
        target_role_note=None,
        company_types=["any"],
        applications_sent_min=None,
        applications_sent_max=None,
        recruiter_contacts=None,
        first_round_interviews=None,
        final_round_interviews=None,
        offers=None,
        emotional_challenge="burnout",
        baseline_anxiety=6,
        preparation_for="general_reset",
    )
    assert "N/A" in result


# ---------------------------------------------------------------------------
# build_onboarding_script_prompt — smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_onboarding_script_prompt_returns_string() -> None:
    result = build_onboarding_script_prompt(
        employment_status="unemployed",
        unemployed_duration="6m",
        job_timeline="asap",
        target_role_category="product_management",
        target_role_note="Senior PM",
        company_types=["startup", "scale_up"],
        applications_sent_min=10,
        applications_sent_max=15,
        recruiter_contacts=3,
        first_round_interviews=2,
        final_round_interviews=1,
        offers=0,
        emotional_challenge="rejection_silence",
        baseline_anxiety=7,
        preparation_for="rejection_recovery",
    )
    assert isinstance(result, str)
    assert "phase1" in result
    assert "phase5" in result


@pytest.mark.unit
def test_build_onboarding_script_prompt_includes_preparation_for() -> None:
    result = build_onboarding_script_prompt(
        employment_status="unemployed",
        unemployed_duration="1m",
        job_timeline="3m",
        target_role_category="sales",
        target_role_note=None,
        company_types=["enterprise"],
        applications_sent_min=20,
        applications_sent_max=25,
        recruiter_contacts=5,
        first_round_interviews=3,
        final_round_interviews=2,
        offers=1,
        emotional_challenge="interview_anxiety",
        baseline_anxiety=8,
        preparation_for="restarting_search",
    )
    assert "restarting_search" in result