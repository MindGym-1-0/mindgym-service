"""Unit tests for session Pydantic models"""
import pytest
from pydantic import ValidationError

from src.types.session import (
    SessionCompleteRequest,
    SessionStartRequest,
    UserUpdateRequest,
)


# --- SessionStartRequest ---

def test_session_start_request_valid():
    req = SessionStartRequest(
        preparation_for='interview_tomorrow',
        current_feeling='nervous',
        desired_feeling='confident',
        time_available='10 minutes',
        pre_score=7,
    )
    assert req.preparation_for == 'interview_tomorrow'
    assert req.pre_score == 7


def test_session_start_request_all_preparation_for_values():
    valid_values = [
        'interview_tomorrow',
        'recruiter_call',
        'networking',
        'salary_negotiation',
        'rejection_recovery',
        'restarting_search',
        'general_reset',
    ]
    for value in valid_values:
        req = SessionStartRequest(
            preparation_for=value,
            current_feeling='okay',
            desired_feeling='great',
            time_available='5 minutes',
            pre_score=5,
        )
        assert req.preparation_for == value


def test_session_start_request_invalid_preparation_for():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='interview_today',
            current_feeling='nervous',
            desired_feeling='confident',
            time_available='10 minutes',
            pre_score=7,
        )


def test_session_start_request_pre_score_boundary_valid():
    for score in [1, 10]:
        req = SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 minutes',
            pre_score=score,
        )
        assert req.pre_score == score


def test_session_start_request_pre_score_too_low():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 minutes',
            pre_score=0,
        )


def test_session_start_request_pre_score_too_high():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 minutes',
            pre_score=11,
        )


# --- SessionCompleteRequest ---

def test_session_complete_request_valid():
    req = SessionCompleteRequest(session_id='abc-123', post_score=8)
    assert req.post_score == 8


def test_session_complete_request_post_score_too_low():
    with pytest.raises(ValidationError):
        SessionCompleteRequest(session_id='abc-123', post_score=0)


def test_session_complete_request_post_score_too_high():
    with pytest.raises(ValidationError):
        SessionCompleteRequest(session_id='abc-123', post_score=11)


# --- UserUpdateRequest ---

def test_user_update_request_all_optional():
    req = UserUpdateRequest()
    assert req.goal is None
    assert req.stage is None
    assert req.anxiety_level is None


def test_user_update_request_partial():
    req = UserUpdateRequest(goal='Get a senior role')
    assert req.goal == 'Get a senior role'
    assert req.stage is None


def test_user_update_request_anxiety_level_out_of_range():
    with pytest.raises(ValidationError):
        UserUpdateRequest(anxiety_level=11)
