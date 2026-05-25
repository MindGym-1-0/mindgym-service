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
        time_available='10 min',
        pre_score=7,
        company='Google',
        role='Engineer',
    )
    assert req.preparation_for == 'interview_tomorrow'
    assert req.pre_score == 7


def test_session_start_request_all_preparation_for_values():
    mode1_types = {'interview_tomorrow', 'recruiter_call'}
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
        kwargs = dict(
            preparation_for=value,
            current_feeling='okay',
            desired_feeling='calm',
            time_available='5 min',
            pre_score=5,
        )
        if value in mode1_types:
            kwargs['company'] = 'Acme'
            kwargs['role'] = 'Engineer'
        req = SessionStartRequest(**kwargs)
        assert req.preparation_for == value


def test_session_start_request_invalid_preparation_for():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='interview_today',
            current_feeling='nervous',
            desired_feeling='confident',
            time_available='10 min',
            pre_score=7,
        )


def test_session_start_request_pre_score_boundary_valid():
    for score in [1, 10]:
        req = SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 min',
            pre_score=score,
        )
        assert req.pre_score == score


def test_session_start_request_pre_score_too_low():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 min',
            pre_score=0,
        )


def test_session_start_request_pre_score_too_high():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='tired',
            desired_feeling='calm',
            time_available='5 min',
            pre_score=11,
        )


def test_session_start_request_all_desired_feeling_values():
    valid_values = ['calm', 'grounded', 'confident', 'focused', 'clear_minded', 'composed']
    for value in valid_values:
        req = SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='anxious',
            desired_feeling=value,
            time_available='5 min',
            pre_score=5,
        )
        assert req.desired_feeling == value


def test_session_start_request_invalid_desired_feeling():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='anxious',
            desired_feeling='happy',
            time_available='5 min',
            pre_score=5,
        )


def test_session_start_request_all_time_available_values():
    for value in ['5 min', '10 min', '15 min']:
        req = SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='anxious',
            desired_feeling='calm',
            time_available=value,
            pre_score=5,
        )
        assert req.time_available == value


def test_session_start_request_invalid_time_available():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='general_reset',
            current_feeling='anxious',
            desired_feeling='calm',
            time_available='20 min',
            pre_score=5,
        )


def test_session_start_request_company_and_role_required_for_mode1():
    with pytest.raises(ValidationError):
        SessionStartRequest(
            preparation_for='interview_tomorrow',
            current_feeling='nervous',
            desired_feeling='confident',
            time_available='10 min',
            pre_score=7,
        )


def test_session_start_request_company_and_role_provided():
    req = SessionStartRequest(
        preparation_for='interview_tomorrow',
        current_feeling='nervous',
        desired_feeling='confident',
        time_available='10 min',
        pre_score=7,
        company='Google',
        role='Staff Engineer',
    )
    assert req.company == 'Google'
    assert req.role == 'Staff Engineer'


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
