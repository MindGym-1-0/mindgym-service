"""Unit tests for user_prompt helpers — pipeline signal and about block."""
import pytest

from src.prompts.user_prompt import _build_about_block, _derive_pipeline_signal


# ---------------------------------------------------------------------------
# _derive_pipeline_signal
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_pipeline_signal_none_when_no_context() -> None:
    assert _derive_pipeline_signal(None) is None


@pytest.mark.unit
def test_pipeline_signal_none_when_empty_context() -> None:
    assert _derive_pipeline_signal({}) is None


@pytest.mark.unit
def test_pipeline_signal_high_apps_no_recruiter_contacts() -> None:
    ctx = {"applications_sent_max": 25, "recruiter_contacts": 0}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've sent many applications but haven't connected with any recruiters yet."


@pytest.mark.unit
def test_pipeline_signal_moderate_apps_no_interviews() -> None:
    ctx = {"applications_sent_max": 15, "recruiter_contacts": 2, "first_round_interviews": 0}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've been applying but haven't reached an interview yet."


@pytest.mark.unit
def test_pipeline_signal_recruiter_contacts_no_interviews() -> None:
    ctx = {"applications_sent_max": 8, "recruiter_contacts": 3, "first_round_interviews": 0}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've made recruiter contacts but haven't converted to interviews."


@pytest.mark.unit
def test_pipeline_signal_first_rounds_no_finals() -> None:
    ctx = {"applications_sent_max": 20, "recruiter_contacts": 4, "first_round_interviews": 3, "final_round_interviews": 0}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've had first-round interviews but haven't advanced further."


@pytest.mark.unit
def test_pipeline_signal_has_first_rounds() -> None:
    ctx = {"applications_sent_max": 20, "recruiter_contacts": 5, "first_round_interviews": 2, "final_round_interviews": 1}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've had first-round interviews — they're getting in the door."


@pytest.mark.unit
def test_pipeline_signal_none_when_missing_apps_and_no_other_data() -> None:
    # No apps, no contacts, no interviews — nothing actionable to say
    ctx = {"applications_sent_max": None, "recruiter_contacts": None, "first_round_interviews": None}
    assert _derive_pipeline_signal(ctx) is None


@pytest.mark.unit
def test_pipeline_signal_treats_missing_fields_as_zero() -> None:
    # Only apps provided — no recruiter_contacts key at all
    ctx = {"applications_sent_max": 30}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've sent many applications but haven't connected with any recruiters yet."


@pytest.mark.unit
def test_pipeline_signal_uses_max_over_min() -> None:
    # max should take precedence over min
    ctx = {"applications_sent_min": 5, "applications_sent_max": 25, "recruiter_contacts": 0}
    result = _derive_pipeline_signal(ctx)
    assert result == "They've sent many applications but haven't connected with any recruiters yet."


# ---------------------------------------------------------------------------
# _build_about_block — pipeline signal appended
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_about_block_includes_pipeline_signal() -> None:
    ctx = {
        "employment_status": "laid_off",
        "unemployed_duration": "3m",
        "job_timeline": "asap",
        "applications_sent_max": 15,
        "recruiter_contacts": 0,
        "first_round_interviews": 0,
        "emotional_challenge": "rejection_silence",
        "target_role_note": "Senior PM in fintech",
        "baseline_anxiety": 7,
    }
    block = _build_about_block(ctx, anxiety_level_before=8)
    assert "They've been applying but haven't reached an interview yet." in block


@pytest.mark.unit
def test_about_block_no_pipeline_signal_when_data_absent() -> None:
    ctx = {
        "employment_status": "employed",
        "emotional_challenge": "uncertainty",
        "baseline_anxiety": 4,
    }
    block = _build_about_block(ctx, anxiety_level_before=4)
    # No pipeline data — signal sentence must not appear
    assert "applying" not in block
    assert "interviews" not in block


@pytest.mark.unit
def test_about_block_pipeline_signal_is_last_before_guardrail() -> None:
    ctx = {
        "employment_status": "laid_off",
        "unemployed_duration": "3m",
        "applications_sent_max": 25,
        "recruiter_contacts": 0,
        "emotional_challenge": "rejection_silence",
        "baseline_anxiety": 6,
    }
    block = _build_about_block(ctx, anxiety_level_before=7)
    prose_line = block.split("\n")[0]
    signal = "They've sent many applications but haven't connected with any recruiters yet."
    # Signal should appear in the prose, just before the guardrail newline
    assert signal in prose_line
