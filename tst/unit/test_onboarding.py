"""Unit tests for onboarding endpoints"""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import create_app
from src.types.models import JobSearchStage, MoodChallenge, OnboardingRequest

_FAKE_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def client():
    """Create a test client with auth bypassed for validation tests."""
    app = create_app()
    app.dependency_overrides[require_current_user_id] = lambda: _FAKE_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: "fake-token"
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_onboard_missing_job_goal(client):
    """Test onboarding with missing job goal"""
    payload = {
        "job_search_stage": "Sending applications",
        "mood": "interview-anxiety",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_missing_job_search_stage(client):
    """Test onboarding with missing job search stage"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "mood": "interview-anxiety",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_missing_mood(client):
    """Test onboarding with missing mood"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": "Sending applications",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_invalid_job_goal(client):
    """Test onboarding with empty job goal"""
    payload = {
        "job_goal": "",
        "job_search_stage": "Sending applications",
        "mood": "interview-anxiety",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_invalid_job_search_stage(client):
    """Test onboarding with invalid job search stage"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": "invalid_stage",
        "mood": "interview-anxiety",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_all_job_search_stages(client):
    """Test all valid job search stage values are accepted by the model"""
    stages = [
        JobSearchStage.SENDING_APPLICATIONS,
        JobSearchStage.GETTING_RECRUITER_CALLS,
        JobSearchStage.IN_INTERVIEWS,
        JobSearchStage.FINAL_ROUNDS_OFFERS,
    ]
    for stage in stages:
        request = OnboardingRequest(
            job_goal="Senior Software Engineer",
            job_search_stage=stage,
            mood="interview-anxiety",
        )
        assert request.job_search_stage == stage


def test_onboard_all_mood_options(client):
    """Test all predefined mood values are valid"""
    moods = [
        MoodChallenge.INTERVIEW_ANXIETY,
        MoodChallenge.OVERTHINKING,
        MoodChallenge.REJECTION,
        MoodChallenge.BURNOUT,
        MoodChallenge.MOTIVATION,
        MoodChallenge.CONFIDENCE,
    ]
    for mood in moods:
        request = OnboardingRequest(
            job_goal="Senior Software Engineer",
            job_search_stage=JobSearchStage.IN_INTERVIEWS,
            mood=mood.value,
        )
        assert request.mood == mood.value


def test_onboard_custom_mood(client):
    """Test onboarding accepts a custom typed mood"""
    request = OnboardingRequest(
        job_goal="Senior Software Engineer",
        job_search_stage=JobSearchStage.IN_INTERVIEWS,
        mood="Feeling overwhelmed and caffeinated",
    )
    assert request.mood == "Feeling overwhelmed and caffeinated"
