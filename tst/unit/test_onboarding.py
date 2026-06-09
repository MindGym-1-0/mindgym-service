"""Unit tests for onboarding API endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.lib.auth_dependencies import get_current_user
from src.types.models import (
    OnboardingGapAnalysis,
    OnboardingFirstSession,
    OnboardingResponse,
)
from src.types.session import SessionScript

_FAKE_USER = {"id": "user-123", "email": "test@example.com"}

_VALID_PAYLOAD = {
    "employment_status": "unemployed",
    "unemployed_duration": "3m",
    "job_timeline": "asap",
    "target_role_category": "product_management",
    "target_role_note": "Senior PM in fintech",
    "company_types": ["startup", "scale_up"],
    "applications_sent_min": 10,
    "applications_sent_max": 15,
    "recruiter_contacts": 3,
    "first_round_interviews": 2,
    "final_round_interviews": 1,
    "offers": 0,
    "emotional_challenge": ["rejection_silence"],
    "baseline_anxiety": 7,
}

_FAKE_SCRIPT = SessionScript(
    phase1="Close your eyes and breathe slowly.",
    phase2="Feel the ground beneath you.",
    phase3="Picture yourself landing the role.",
    phase4="Recall a time you succeeded under pressure.",
    phase5="You are ready. Step forward.",
)

_FAKE_GAP_ANALYSIS = {
    "mindset_gap": "Rejection sensitivity",
    "mindset_gap_detail": "Rejections are eroding confidence faster than applications rebuild it.",
    "hunting_gap": "Screening → Final round",
    "hunting_gap_detail": "12 applications → 2 screenings → 1 final. The bottleneck is at the final stage.",
    "baseline_anxiety_note": "High — Maya will aim to bring this to 2–3 through consistent session work.",
    "session_title": "Envisioning success — breaking the rejection spiral",
    "session_description": "A 10-minute guided visualisation session. Maya will walk you through envisioning yourself succeeding in your next final round.",
    "session_tags": ["10 minutes", "Visualisation", "Rejection recovery"],
}

_FAKE_RESPONSE = OnboardingResponse(
    success=True,
    user_id="user-123",
    gap_analysis=OnboardingGapAnalysis(
        mindset_gap="Rejection sensitivity",
        mindset_gap_detail="Rejections are eroding confidence.",
        hunting_gap="Screening → Final round",
        hunting_gap_detail="Bottleneck at the final stage.",
        baseline_anxiety_note="High — Maya will aim to reduce this.",
    ),
    first_session=OnboardingFirstSession(
        session_id="session-abc",
        preparation_for="rejection_recovery",
        session_title="Envisioning success — breaking the rejection spiral",
        session_description="A 10-minute guided visualisation session.",
        session_tags=["10 minutes", "Visualisation", "Rejection recovery"],
        script=_FAKE_SCRIPT,
    ),
)


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/onboard — happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_onboard_returns_201_with_full_response(client) -> None:
    """POST /api/onboard must return 201 with gap analysis and first session."""
    with patch("src.api.onboarding.asyncio") as mock_asyncio, \
         patch("src.api.onboarding.derive_preparation_for", return_value="rejection_recovery"), \
         patch("src.api.onboarding.insert_onboarding_session", new_callable=AsyncMock, return_value="session-abc"):

        mock_asyncio.to_thread = AsyncMock(return_value=None)
        mock_asyncio.wait_for = AsyncMock(return_value=(_FAKE_GAP_ANALYSIS, _FAKE_SCRIPT))

        response = client.post("/api/onboard", json=_VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["user_id"] == "user-123"
    assert "gap_analysis" in body
    assert "first_session" in body


@pytest.mark.unit
def test_onboard_returns_401_when_unauthenticated() -> None:
    """POST /api/onboard must return 401 when no auth token is provided."""
    client = TestClient(app)
    response = client.post("/api/onboard", json=_VALID_PAYLOAD)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/onboard — validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_onboard_requires_unemployed_duration_when_not_employed(client) -> None:
    """POST /api/onboard must return 422 when unemployed but duration is missing."""
    payload = {**_VALID_PAYLOAD, "unemployed_duration": None}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_allows_missing_duration_when_employed(client) -> None:
    """POST /api/onboard must accept employed status without unemployed_duration."""
    payload = {**_VALID_PAYLOAD, "employment_status": "employed", "unemployed_duration": None}
    with patch("src.api.onboarding.asyncio") as mock_asyncio, \
         patch("src.api.onboarding.derive_preparation_for", return_value="general_reset"), \
         patch("src.api.onboarding.insert_onboarding_session", new_callable=AsyncMock, return_value="session-abc"):

        mock_asyncio.to_thread = AsyncMock(return_value=None)
        mock_asyncio.wait_for = AsyncMock(return_value=(_FAKE_GAP_ANALYSIS, _FAKE_SCRIPT))
        response = client.post("/api/onboard", json=payload)

    assert response.status_code == 201


@pytest.mark.unit
def test_onboard_rejects_invalid_employment_status(client) -> None:
    """POST /api/onboard must return 422 for unknown employment_status."""
    payload = {**_VALID_PAYLOAD, "employment_status": "retired"}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_rejects_empty_company_types(client) -> None:
    """POST /api/onboard must return 422 when company_types is empty."""
    payload = {**_VALID_PAYLOAD, "company_types": []}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_rejects_invalid_emotional_challenge(client) -> None:
    """POST /api/onboard must return 422 for unknown emotional_challenge."""
    payload = {**_VALID_PAYLOAD, "emotional_challenge": ["loneliness"]}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_rejects_baseline_anxiety_out_of_range(client) -> None:
    """POST /api/onboard must return 422 when baseline_anxiety is outside 1–10."""
    payload = {**_VALID_PAYLOAD, "baseline_anxiety": 11}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_rejects_invalid_job_timeline(client) -> None:
    """POST /api/onboard must return 422 for unknown job_timeline."""
    payload = {**_VALID_PAYLOAD, "job_timeline": "2_years"}
    response = client.post("/api/onboard", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_onboard_accepts_optional_target_role_note_as_none(client) -> None:
    """POST /api/onboard must accept a missing target_role_note."""
    payload = {**_VALID_PAYLOAD, "target_role_note": None}
    with patch("src.api.onboarding.asyncio") as mock_asyncio, \
         patch("src.api.onboarding.derive_preparation_for", return_value="rejection_recovery"), \
         patch("src.api.onboarding.insert_onboarding_session", new_callable=AsyncMock, return_value="session-abc"):

        mock_asyncio.to_thread = AsyncMock(return_value=None)
        mock_asyncio.wait_for = AsyncMock(return_value=(_FAKE_GAP_ANALYSIS, _FAKE_SCRIPT))
        response = client.post("/api/onboard", json=payload)

    assert response.status_code == 201