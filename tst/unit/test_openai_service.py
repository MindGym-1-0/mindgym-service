"""Unit tests for openai_service — guard verification (Mode 1, hype, min_length)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from src.lib.openai_service import generate_script
from src.types.session import SessionScript

_VALID_RESPONSE = (
    '{"phase1": "Close your eyes and take a slow breath in.",'
    ' "phase2": "Feel the ground beneath you, steady and real.",'
    ' "phase3": "Picture yourself at Stripe for your PM role.",'
    ' "phase4": "Recall a time you performed under pressure and delivered.",'
    ' "phase5": "You are ready for Stripe as a PM today."}'
)

_COMMON_ARGS = dict(
    preparation_for="general_reset",
    current_feeling="overwhelmed",
    desired_feeling="grounded",
    time_available="10 min",
    anxiety_level_before=5,
    company=None,
    role=None,
)

_MODE1_ARGS = dict(
    preparation_for="interview_tomorrow",
    current_feeling="overwhelmed",
    desired_feeling="confident",
    time_available="10 min",
    anxiety_level_before=5,
    company="Stripe",
    role="PM",
)

# build_prompt_parts is imported locally inside generate_script — patch at source
_PROMPT_PATCH = "src.lib.prompt_builder.build_prompt_parts"


# --- success path ---


@pytest.mark.unit
def test_generate_script_returns_session_script_on_valid_response() -> None:
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=_VALID_RESPONSE):
        result = generate_script(**_MODE1_ARGS)

    assert isinstance(result, SessionScript)
    assert result.phase1 == "Close your eyes and take a slow breath in."
    assert result.phase3 == "Picture yourself at Stripe for your PM role."


# --- _chat failure ---


@pytest.mark.unit
def test_generate_script_returns_none_when_chat_fails() -> None:
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=None):
        result = generate_script(**_COMMON_ARGS)

    assert result is None


# --- Mode 1 company+role enforcement ---


@pytest.mark.unit
def test_generate_script_returns_none_when_mode1_output_missing_company_and_role() -> None:
    raw = (
        '{"phase1": "Close your eyes and breathe slowly.",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself in the interview room.",'
        ' "phase4": "Recall a moment when you performed well.",'
        ' "phase5": "You are ready for this moment today."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**_MODE1_ARGS)

    assert result is None


@pytest.mark.unit
def test_generate_script_returns_none_when_mode1_output_missing_role() -> None:
    raw = (
        '{"phase1": "Close your eyes and breathe.",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself walking into Stripe today.",'
        ' "phase4": "Recall a moment when you performed well.",'
        ' "phase5": "You are ready for Stripe and this moment."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**_MODE1_ARGS)

    assert result is None


@pytest.mark.unit
def test_generate_script_passes_mode2_without_company_or_role() -> None:
    raw = (
        '{"phase1": "Close your eyes and breathe slowly.",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself in a place you feel strong.",'
        ' "phase4": "Recall a moment when you showed up for yourself.",'
        ' "phase5": "You have everything you need right now today."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**_COMMON_ARGS)

    assert isinstance(result, SessionScript)


# --- hype guard ---


@pytest.mark.unit
def test_generate_script_returns_none_when_hype_guard_fires_at_high_anxiety() -> None:
    raw = (
        '{"phase1": "You are pumped and ready to crush it today!",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself strong and capable in any room.",'
        ' "phase4": "Recall a time you delivered under pressure.",'
        ' "phase5": "You have everything you need for this moment."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**{**_COMMON_ARGS, "anxiety_level_before": 8})

    assert result is None


@pytest.mark.unit
def test_generate_script_allows_hype_words_at_low_anxiety() -> None:
    raw = (
        '{"phase1": "You are pumped and ready to crush it today!",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself strong and capable in any room.",'
        ' "phase4": "Recall a time you delivered under pressure.",'
        ' "phase5": "You have everything you need for this moment."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**{**_COMMON_ARGS, "anxiety_level_before": 3})

    assert isinstance(result, SessionScript)


# --- min_length guard (Pydantic) ---


@pytest.mark.unit
def test_generate_script_returns_none_when_phase_is_too_short() -> None:
    raw = (
        '{"phase1": "Breathe.",'
        ' "phase2": "Feel the ground beneath you, steady and real.",'
        ' "phase3": "Picture yourself strong and capable in any room.",'
        ' "phase4": "Recall a time you delivered under pressure.",'
        ' "phase5": "You have everything you need for this moment."}'
    )
    with patch(_PROMPT_PATCH, return_value=("s", "u")), \
         patch("src.lib.openai_service._chat", return_value=raw):
        result = generate_script(**_COMMON_ARGS)

    assert result is None
