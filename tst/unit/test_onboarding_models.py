"""Unit tests for onboarding Pydantic models."""
import pytest
from pydantic import ValidationError
from src.types.models import OnboardingRequest


_VALID = {
    "employment_status": "unemployed",
    "unemployed_duration": "3m",
    "job_timeline": "asap",
    "target_role_category": "product_management",
    "company_types": ["startup"],
    "emotional_challenge": ["rejection_silence"],
    "baseline_anxiety": 7,
}


# ---------------------------------------------------------------------------
# employment_status
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_valid_employment_status_employed() -> None:
    req = OnboardingRequest(**{**_VALID, "employment_status": "employed", "unemployed_duration": None})
    assert req.employment_status == "employed"


@pytest.mark.unit
def test_valid_employment_status_unemployed() -> None:
    req = OnboardingRequest(**_VALID)
    assert req.employment_status == "unemployed"


@pytest.mark.unit
def test_valid_employment_status_laid_off() -> None:
    req = OnboardingRequest(**{**_VALID, "employment_status": "laid_off"})
    assert req.employment_status == "laid_off"


@pytest.mark.unit
def test_invalid_employment_status_raises() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "employment_status": "freelance"})


# ---------------------------------------------------------------------------
# unemployed_duration validator
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_unemployed_duration_required_when_unemployed() -> None:
    with pytest.raises(ValidationError, match="unemployed_duration is required"):
        OnboardingRequest(**{**_VALID, "unemployed_duration": None})


@pytest.mark.unit
def test_unemployed_duration_required_when_laid_off() -> None:
    with pytest.raises(ValidationError, match="unemployed_duration is required"):
        OnboardingRequest(**{**_VALID, "employment_status": "laid_off", "unemployed_duration": None})


@pytest.mark.unit
def test_unemployed_duration_not_required_when_employed() -> None:
    req = OnboardingRequest(**{**_VALID, "employment_status": "employed", "unemployed_duration": None})
    assert req.unemployed_duration is None


@pytest.mark.unit
def test_unemployed_duration_accepts_1y_plus() -> None:
    req = OnboardingRequest(**{**_VALID, "unemployed_duration": "1y+"})
    assert req.unemployed_duration == "1y+"


@pytest.mark.unit
def test_unemployed_duration_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "unemployed_duration": "5y"})


# ---------------------------------------------------------------------------
# company_types
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_company_types_accepts_multiple() -> None:
    req = OnboardingRequest(**{**_VALID, "company_types": ["startup", "large_tech", "enterprise"]})
    assert len(req.company_types) == 3


@pytest.mark.unit
def test_company_types_rejects_empty_list() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "company_types": []})


@pytest.mark.unit
def test_company_types_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "company_types": ["ngo"]})


# ---------------------------------------------------------------------------
# baseline_anxiety
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_baseline_anxiety_accepts_min_value() -> None:
    req = OnboardingRequest(**{**_VALID, "baseline_anxiety": 1})
    assert req.baseline_anxiety == 1


@pytest.mark.unit
def test_baseline_anxiety_accepts_max_value() -> None:
    req = OnboardingRequest(**{**_VALID, "baseline_anxiety": 10})
    assert req.baseline_anxiety == 10


@pytest.mark.unit
def test_baseline_anxiety_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "baseline_anxiety": 0})


@pytest.mark.unit
def test_baseline_anxiety_rejects_eleven() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "baseline_anxiety": 11})


# ---------------------------------------------------------------------------
# optional fields
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_target_role_note_is_optional() -> None:
    req = OnboardingRequest(**{**_VALID, "target_role_note": None})
    assert req.target_role_note is None


@pytest.mark.unit
def test_activity_counters_are_optional() -> None:
    req = OnboardingRequest(**_VALID)
    assert req.recruiter_contacts is None
    assert req.first_round_interviews is None
    assert req.offers is None


# ---------------------------------------------------------------------------
# emotional_challenge
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_emotional_challenge_accepts_single_value() -> None:
    req = OnboardingRequest(**{**_VALID, "emotional_challenge": ["interview_anxiety"]})
    assert req.emotional_challenge == ["interview_anxiety"]


@pytest.mark.unit
def test_emotional_challenge_accepts_two_values() -> None:
    req = OnboardingRequest(**{**_VALID, "emotional_challenge": ["burnout", "imposter_syndrome"]})
    assert len(req.emotional_challenge) == 2


@pytest.mark.unit
def test_emotional_challenge_rejects_more_than_two() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "emotional_challenge": ["burnout", "imposter_syndrome", "uncertainty"]})


@pytest.mark.unit
def test_emotional_challenge_rejects_empty_list() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "emotional_challenge": []})


@pytest.mark.unit
def test_emotional_challenge_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        OnboardingRequest(**{**_VALID, "emotional_challenge": ["loneliness"]})