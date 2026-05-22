"""Unit tests for onboarding endpoints"""
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
from src.types.models import JobSearchStage, AnxietyLevel, OnboardingRequest


@pytest.fixture
def client():
    """Create a test client"""
    app = create_app()
    return TestClient(app)


def test_onboard_success(client):
    """Test successful onboarding"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
        "anxiety_level": AnxietyLevel.MODERATE,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "user_id" in data
    assert data["message"] == "Onboarding completed successfully"


def test_onboard_missing_job_goal(client):
    """Test onboarding with missing job goal"""
    payload = {
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
        "anxiety_level": AnxietyLevel.MODERATE,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_missing_job_search_stage(client):
    """Test onboarding with missing job search stage"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "anxiety_level": AnxietyLevel.MODERATE,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_missing_anxiety_level(client):
    """Test onboarding with missing anxiety level"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_invalid_job_goal(client):
    """Test onboarding with invalid job goal (empty string)"""
    payload = {
        "job_goal": "",
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
        "anxiety_level": AnxietyLevel.MODERATE,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_invalid_job_search_stage(client):
    """Test onboarding with invalid job search stage"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": "invalid_stage",
        "anxiety_level": AnxietyLevel.MODERATE,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_invalid_anxiety_level(client):
    """Test onboarding with invalid anxiety level"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
        "anxiety_level": "extreme",
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


def test_onboard_all_job_search_stages(client):
    """Test onboarding with all valid job search stages"""
    stages = [
        JobSearchStage.EXPLORING,
        JobSearchStage.PREPARING,
        JobSearchStage.ACTIVELY_SEARCHING,
        JobSearchStage.INTERVIEWING,
    ]
    for stage in stages:
        payload = {
            "job_goal": "Senior Software Engineer",
            "job_search_stage": stage,
            "anxiety_level": AnxietyLevel.MODERATE,
        }
        response = client.post("/api/onboard", json=payload)
        assert response.status_code == 201


def test_onboard_all_anxiety_levels(client):
    """Test onboarding with all valid anxiety levels"""
    levels = [
        AnxietyLevel.LOW,
        AnxietyLevel.MODERATE,
        AnxietyLevel.HIGH,
        AnxietyLevel.VERY_HIGH,
    ]
    for level in levels:
        payload = {
            "job_goal": "Senior Software Engineer",
            "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
            "anxiety_level": level,
        }
        response = client.post("/api/onboard", json=payload)
        assert response.status_code == 201


def test_onboard_numeric_anxiety_level(client):
    """Test onboarding accepts numeric anxiety levels"""
    payload = {
        "job_goal": "Senior Software Engineer",
        "job_search_stage": JobSearchStage.ACTIVELY_SEARCHING,
        "anxiety_level": 6,
    }
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 201


def test_anxiety_level_enum_normalizes_to_score():
    """Test anxiety level enum values normalize to numeric scores"""
    request = OnboardingRequest(
        job_goal="Senior Software Engineer",
        job_search_stage=JobSearchStage.ACTIVELY_SEARCHING,
        anxiety_level=AnxietyLevel.MODERATE,
    )
    assert request.anxiety_level == 4
