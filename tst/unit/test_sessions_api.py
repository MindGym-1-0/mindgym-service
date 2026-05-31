"""Unit tests for sessions API route handlers."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.lib.auth_dependencies import get_current_user
from src.types.session import (
    SessionCompleteResponse,
    SessionDetail,
    SessionHistoryItem,
    SessionScript,
    SessionStartResponse,
)

_FAKE_USER = {'id': 'user-123', 'email': 'test@example.com'}
_FAKE_SCRIPT = SessionScript(
    phase1='Close your eyes and take a slow breath.',
    phase2='Feel the ground beneath you, steady and real.',
    phase3='Picture yourself at Stripe as a PM.',
    phase4='Recall a time you delivered under pressure.',
    phase5='You are ready for Stripe as a PM.',
)
_FAKE_START_RESPONSE = SessionStartResponse(
    session_id='session-abc',
    script=_FAKE_SCRIPT,
    mode='interview_tomorrow',
)
_FAKE_COMPLETE_RESPONSE = SessionCompleteResponse(
    session_id='session-abc',
    anxiety_level_before=3,
    anxiety_level_after=8,
    anxiety_level_delta=5,
    message='Session complete. Anxiety shifted by +5.',
)
_FAKE_HISTORY = [
    SessionHistoryItem(
        id='session-abc',
        preparation_for='interview_tomorrow',
        anxiety_level_before=3,
        anxiety_level_after=8,
        anxiety_level_delta=5,
        completed_at='2026-05-24T10:00:00+00:00',
        created_at='2026-05-24T09:00:00+00:00',
    )
]
_FAKE_DETAIL = SessionDetail(
    id='session-abc',
    preparation_for='interview_tomorrow',
    current_feeling='overwhelmed',
    desired_feeling='confident',
    time_available='10 min',
    company='Stripe',
    role='PM',
    anxiety_level_before=3,
    anxiety_level_after=8,
    anxiety_level_delta=5,
    script=_FAKE_SCRIPT,
    completed_at='2026-05-24T10:00:00+00:00',
    created_at='2026-05-24T09:00:00+00:00',
)

_START_PAYLOAD = {
    'preparation_for': 'interview_tomorrow',
    'current_feeling': 'overwhelmed',
    'desired_feeling': 'confident',
    'time_available': '10 min',
    'anxiety_level_before': 3,
    'company': 'Stripe',
    'role': 'PM',
}
_COMPLETE_PAYLOAD = {'session_id': 'session-abc', 'anxiety_level_after': 8}


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/sessions/start
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_start_session_returns_201_with_script(client) -> None:
    """POST /api/sessions/start must return 201 with session_id and script."""
    with patch('src.api.sessions.start_session', new_callable=AsyncMock, return_value=_FAKE_START_RESPONSE):
        response = client.post('/api/sessions/start', json=_START_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body['session_id'] == 'session-abc'
    assert body['mode'] == 'interview_tomorrow'
    assert body['script']['phase1'] == 'Close your eyes and take a slow breath.'


@pytest.mark.unit
def test_start_session_returns_401_when_unauthenticated() -> None:
    """POST /api/sessions/start must return 401 when no auth token is provided."""
    client = TestClient(app)
    response = client.post('/api/sessions/start', json=_START_PAYLOAD)
    assert response.status_code == 401


@pytest.mark.unit
def test_start_session_returns_503_when_service_raises(client) -> None:
    """POST /api/sessions/start must return 503 when session generation fails entirely."""
    with patch('src.api.sessions.start_session', new_callable=AsyncMock, side_effect=RuntimeError('both failed')):
        response = client.post('/api/sessions/start', json=_START_PAYLOAD)

    assert response.status_code == 503


@pytest.mark.unit
def test_start_session_returns_400_on_invalid_payload(client) -> None:
    """POST /api/sessions/start must return 422 for an invalid preparation_for value."""
    bad_payload = {**_START_PAYLOAD, 'preparation_for': 'not_a_real_type'}
    with patch('src.api.sessions.start_session', new_callable=AsyncMock, return_value=_FAKE_START_RESPONSE):
        response = client.post('/api/sessions/start', json=bad_payload)

    assert response.status_code == 422


@pytest.mark.unit
def test_start_session_returns_422_when_mode1_missing_company(client) -> None:
    """POST /api/sessions/start must return 422 when interview_tomorrow is submitted without company."""
    bad_payload = {**_START_PAYLOAD, 'company': None, 'role': None}
    with patch('src.api.sessions.start_session', new_callable=AsyncMock, return_value=_FAKE_START_RESPONSE):
        response = client.post('/api/sessions/start', json=bad_payload)

    assert response.status_code == 422


@pytest.mark.unit
def test_start_session_allows_missing_company_for_general_reset(client) -> None:
    """POST /api/sessions/start must accept general_reset without company or role."""
    general_payload = {
        'preparation_for': 'general_reset',
        'current_feeling': 'overwhelmed',
        'desired_feeling': 'calm',
        'time_available': '5 min',
        'anxiety_level_before': 5,
    }
    with patch('src.api.sessions.start_session', new_callable=AsyncMock, return_value=_FAKE_START_RESPONSE):
        response = client.post('/api/sessions/start', json=general_payload)

    assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/sessions/complete
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_complete_session_returns_200_with_anxiety_level_delta(client) -> None:
    """POST /api/sessions/complete must return 200 with before, after, and delta."""
    with patch('src.api.sessions.complete_session', new_callable=AsyncMock, return_value=_FAKE_COMPLETE_RESPONSE):
        response = client.post('/api/sessions/complete', json=_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body['anxiety_level_delta'] == 5
    assert body['anxiety_level_before'] == 3
    assert body['anxiety_level_after'] == 8


@pytest.mark.unit
def test_complete_session_returns_404_when_not_found(client) -> None:
    """POST /api/sessions/complete must return 404 when session does not exist."""
    with patch('src.api.sessions.complete_session', new_callable=AsyncMock, side_effect=LookupError('not found')):
        response = client.post('/api/sessions/complete', json=_COMPLETE_PAYLOAD)

    assert response.status_code == 404


@pytest.mark.unit
def test_complete_session_returns_401_when_unauthenticated() -> None:
    """POST /api/sessions/complete must return 401 without auth."""
    client = TestClient(app)
    response = client.post('/api/sessions/complete', json=_COMPLETE_PAYLOAD)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/sessions/history
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_history_returns_200_with_list(client) -> None:
    """GET /api/sessions/history must return 200 with a list of session summaries."""
    with patch('src.api.sessions.fetch_session_history', new_callable=AsyncMock, return_value=_FAKE_HISTORY):
        response = client.get('/api/sessions/history')

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]['id'] == 'session-abc'
    assert body[0]['anxiety_level_delta'] == 5


@pytest.mark.unit
def test_get_history_returns_empty_list_when_no_sessions(client) -> None:
    """GET /api/sessions/history must return an empty list when user has no sessions."""
    with patch('src.api.sessions.fetch_session_history', new_callable=AsyncMock, return_value=[]):
        response = client.get('/api/sessions/history')

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_get_history_returns_401_when_unauthenticated() -> None:
    """GET /api/sessions/history must return 401 without auth."""
    client = TestClient(app)
    response = client.get('/api/sessions/history')
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_session_detail_returns_200_with_script(client) -> None:
    """GET /api/sessions/{session_id} must return full session including script phases."""
    with patch('src.api.sessions.fetch_session_detail', new_callable=AsyncMock, return_value=_FAKE_DETAIL):
        response = client.get('/api/sessions/session-abc')

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == 'session-abc'
    assert body['script']['phase3'] == 'Picture yourself at Stripe as a PM.'


@pytest.mark.unit
def test_get_session_detail_returns_404_when_not_found(client) -> None:
    """GET /api/sessions/{session_id} must return 404 when session does not exist."""
    with patch('src.api.sessions.fetch_session_detail', new_callable=AsyncMock, side_effect=LookupError('not found')):
        response = client.get('/api/sessions/missing-id')

    assert response.status_code == 404


@pytest.mark.unit
def test_get_session_detail_returns_401_when_unauthenticated() -> None:
    """GET /api/sessions/{session_id} must return 401 without auth."""
    client = TestClient(app)
    response = client.get('/api/sessions/session-abc')
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/users/me
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_patch_user_me_returns_200(client) -> None:
    """PATCH /api/users/me must return 200 when update succeeds."""
    with patch('src.api.sessions.update_user_profile', new_callable=AsyncMock, return_value=None):
        response = client.patch('/api/users/me', json={'goal': 'Land a senior PM role'})

    assert response.status_code == 200


@pytest.mark.unit
def test_patch_user_me_accepts_partial_update(client) -> None:
    """PATCH /api/users/me must accept a body with only some fields set."""
    with patch('src.api.sessions.update_user_profile', new_callable=AsyncMock, return_value=None):
        response = client.patch('/api/users/me', json={'stage': 'active'})

    assert response.status_code == 200


@pytest.mark.unit
def test_patch_user_me_returns_401_when_unauthenticated() -> None:
    """PATCH /api/users/me must return 401 without auth."""
    client = TestClient(app)
    response = client.patch('/api/users/me', json={'goal': 'something'})
    assert response.status_code == 401
