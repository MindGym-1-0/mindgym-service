"""Unit tests for sessions API route handlers."""
from types import SimpleNamespace
from uuid import UUID

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.sessions as sessions_module
from src.api.users import router as users_router
from src.lib.auth import require_current_user_id, require_current_user_token
from src.lib.elevenlabs_service import ElevenLabsError
from src.lib.auth_dependencies import get_current_user
from src.types.session import (
    SessionCompleteResponse,
    SessionDetail,
    SessionHistoryItem,
    SessionScript,
    SessionStartResponse,
)

_FAKE_USER = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'test@example.com'}
_FAKE_USER_ID = UUID(_FAKE_USER['id'])
_FAKE_TOKEN = 'fake-token'
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


class _FakeInterviewQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.filters: list[tuple[str, object]] = []

    def select(self, _fields: str):
        return self

    def eq(self, field: str, value: object):
        self.filters.append((field, value))
        return self

    def limit(self, _value: int):
        return self

    def execute(self):
        rows = list(self._rows)
        for field, value in self.filters:
            rows = [row for row in rows if row.get(field) == value]
        return SimpleNamespace(data=rows[:1])


class _FakeInterviewClient:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def table(self, table_name: str):
        assert table_name == 'interviews'
        return _FakeInterviewQuery(self.rows)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(sessions_module.router)
    app.include_router(users_router)
    return app


@pytest.fixture
def client():
    app = _build_test_app()
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    app.dependency_overrides[require_current_user_id] = lambda: _FAKE_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: _FAKE_TOKEN
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
    client = TestClient(_build_test_app())
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


@pytest.mark.unit
def test_start_session_rejection_recovery_uses_company_and_role_from_interview(client) -> None:
    """POST /api/sessions/start must hydrate company and role from the owned interview."""
    recovery_payload = {
        'preparation_for': 'rejection_recovery',
        'current_feeling': 'discouraged',
        'desired_feeling': 'grounded',
        'time_available': '10 min',
        'anxiety_level_before': 7,
        'interview_id': '22222222-2222-2222-2222-222222222222',
        'company': 'WrongCo',
        'role': 'WrongRole',
    }
    recovery_response = SessionStartResponse(
        session_id='session-recovery',
        script=_FAKE_SCRIPT,
        mode='rejection_recovery',
    )

    fake_client = _FakeInterviewClient(
        [
            {
                'id': '22222222-2222-2222-2222-222222222222',
                'user_id': _FAKE_USER['id'],
                'company': 'Stripe',
                'role': 'PM',
            }
        ]
    )

    with (
        patch('src.api.sessions.get_supabase_user_client', return_value=fake_client),
        patch(
            'src.api.sessions.start_session',
            new_callable=AsyncMock,
            return_value=recovery_response,
        ) as mock_start,
    ):
        response = client.post('/api/sessions/start', json=recovery_payload)

    assert response.status_code == 201
    called_user_id, called_payload = mock_start.await_args.args
    assert called_user_id == _FAKE_USER['id']
    assert called_payload.preparation_for == 'rejection_recovery'
    assert str(called_payload.interview_id) == recovery_payload['interview_id']
    assert called_payload.company == 'Stripe'
    assert called_payload.role == 'PM'


@pytest.mark.unit
def test_start_session_rejection_recovery_returns_404_when_interview_missing(client) -> None:
    """POST /api/sessions/start must return 404 when the linked interview is missing."""
    recovery_payload = {
        'preparation_for': 'rejection_recovery',
        'current_feeling': 'discouraged',
        'desired_feeling': 'grounded',
        'time_available': '10 min',
        'anxiety_level_before': 7,
        'interview_id': '22222222-2222-2222-2222-222222222222',
    }

    fake_client = _FakeInterviewClient([])

    with (
        patch('src.api.sessions.get_supabase_user_client', return_value=fake_client),
        patch('src.api.sessions.start_session', new_callable=AsyncMock) as mock_start,
    ):
        response = client.post('/api/sessions/start', json=recovery_payload)

    assert response.status_code == 404
    assert response.json() == {'detail': 'Interview not found.'}
    mock_start.assert_not_awaited()


@pytest.mark.unit
def test_start_session_rejection_recovery_normalizes_blank_company_and_role_to_none(client) -> None:
    """POST /api/sessions/start should turn blank interview company/role into None."""
    recovery_payload = {
        'preparation_for': 'rejection_recovery',
        'current_feeling': 'discouraged',
        'desired_feeling': 'grounded',
        'time_available': '10 min',
        'anxiety_level_before': 7,
        'interview_id': '22222222-2222-2222-2222-222222222222',
        'company': 'WrongCo',
        'role': 'WrongRole',
    }
    recovery_response = SessionStartResponse(
        session_id='session-recovery',
        script=_FAKE_SCRIPT,
        mode='rejection_recovery',
    )

    fake_client = _FakeInterviewClient(
        [
            {
                'id': '22222222-2222-2222-2222-222222222222',
                'user_id': _FAKE_USER['id'],
                'company': '   ',
                'role': '',
            }
        ]
    )

    with (
        patch('src.api.sessions.get_supabase_user_client', return_value=fake_client),
        patch(
            'src.api.sessions.start_session',
            new_callable=AsyncMock,
            return_value=recovery_response,
        ) as mock_start,
    ):
        response = client.post('/api/sessions/start', json=recovery_payload)

    assert response.status_code == 201
    _called_user_id, called_payload = mock_start.await_args.args
    assert called_payload.company is None
    assert called_payload.role is None


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
    client = TestClient(_build_test_app())
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
    client = TestClient(_build_test_app())
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
    client = TestClient(_build_test_app())
    response = client.get('/api/sessions/session-abc')
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/users/me
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_patch_user_me_returns_200(client) -> None:
    """PATCH /api/users/me must return 200 when update succeeds."""
    with patch('src.api.users.update_user_profile', new_callable=AsyncMock, return_value=None):
        response = client.patch('/api/users/me', json={'goal': 'Land a senior PM role'})

    assert response.status_code == 200


@pytest.mark.unit
def test_patch_user_me_accepts_partial_update(client) -> None:
    """PATCH /api/users/me must accept a body with only some fields set."""
    with patch('src.api.users.update_user_profile', new_callable=AsyncMock, return_value=None):
        response = client.patch('/api/users/me', json={'stage': 'active'})

    assert response.status_code == 200


@pytest.mark.unit
def test_patch_user_me_returns_401_when_unauthenticated() -> None:
    """PATCH /api/users/me must return 401 without auth."""
    client = TestClient(_build_test_app())
    response = client.patch('/api/users/me', json={'goal': 'something'})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}/audio/{phase}
# ---------------------------------------------------------------------------

def _configured_settings() -> MagicMock:
    m = MagicMock()
    m.elevenlabs_api_key = 'test-key'
    m.elevenlabs_voice_id = 'test-voice'
    return m


async def _fake_audio_stream(_text: str):
    yield b'mp3bytes'


async def _error_audio_stream(_text: str):
    raise ElevenLabsError('ElevenLabs unavailable')
    yield  # makes this an async generator


@pytest.mark.unit
def test_get_phase_audio_returns_200_with_audio_mpeg(client) -> None:
    """GET /audio/{phase} must return 200, audio/mpeg, and Cache-Control: no-store."""
    with (
        patch('src.api.sessions.fetch_phase_text', new_callable=AsyncMock, return_value='Close your eyes.'),
        patch('src.api.sessions.stream_phase_audio', side_effect=_fake_audio_stream),
        patch('src.api.sessions.get_settings', return_value=_configured_settings()),
    ):
        response = client.get('/api/sessions/session-abc/audio/1')

    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'
    assert response.headers['cache-control'] == 'no-store'
    assert response.content == b'mp3bytes'


@pytest.mark.unit
def test_get_phase_audio_returns_422_when_phase_is_zero(client) -> None:
    """GET /audio/0 must return 422 — phase must be between 1 and 5."""
    response = client.get('/api/sessions/session-abc/audio/0')
    assert response.status_code == 422


@pytest.mark.unit
def test_get_phase_audio_returns_422_when_phase_is_six(client) -> None:
    """GET /audio/6 must return 422 — phase must be between 1 and 5."""
    response = client.get('/api/sessions/session-abc/audio/6')
    assert response.status_code == 422


@pytest.mark.unit
def test_get_phase_audio_returns_404_when_session_not_found(client) -> None:
    """GET /audio/{phase} must return 404 when session does not exist."""
    with patch(
        'src.api.sessions.fetch_phase_text',
        new_callable=AsyncMock,
        side_effect=LookupError('Session not found.'),
    ):
        response = client.get('/api/sessions/missing-id/audio/1')
    assert response.status_code == 404


@pytest.mark.unit
def test_get_phase_audio_returns_404_when_session_belongs_to_another_user(client) -> None:
    """GET /audio/{phase} must return 404 when session belongs to a different user."""
    with patch(
        'src.api.sessions.fetch_phase_text',
        new_callable=AsyncMock,
        side_effect=LookupError('Session not found.'),
    ):
        response = client.get('/api/sessions/other-user-session/audio/2')
    assert response.status_code == 404


@pytest.mark.unit
def test_get_phase_audio_returns_400_when_phase_text_is_empty(client) -> None:
    """GET /audio/{phase} must return 400 when phase text is empty in the DB."""
    with patch(
        'src.api.sessions.fetch_phase_text',
        new_callable=AsyncMock,
        side_effect=ValueError('Phase 3 text is empty.'),
    ):
        response = client.get('/api/sessions/session-abc/audio/3')
    assert response.status_code == 400


@pytest.mark.unit
def test_get_phase_audio_returns_503_when_elevenlabs_not_configured(client) -> None:
    """GET /audio/{phase} must return 503 when ElevenLabs credentials are missing."""
    unconfigured = MagicMock()
    unconfigured.elevenlabs_api_key = None
    unconfigured.elevenlabs_voice_id = 'test-voice'

    with (
        patch('src.api.sessions.fetch_phase_text', new_callable=AsyncMock, return_value='Close your eyes.'),
        patch('src.api.sessions.get_settings', return_value=unconfigured),
    ):
        response = client.get('/api/sessions/session-abc/audio/1')
    assert response.status_code == 503


@pytest.mark.unit
def test_get_phase_audio_returns_503_when_elevenlabs_raises(client) -> None:
    """GET /audio/{phase} must return 503 when ElevenLabs service raises."""
    with (
        patch('src.api.sessions.fetch_phase_text', new_callable=AsyncMock, return_value='Close your eyes.'),
        patch('src.api.sessions.stream_phase_audio', side_effect=_error_audio_stream),
        patch('src.api.sessions.get_settings', return_value=_configured_settings()),
    ):
        response = client.get('/api/sessions/session-abc/audio/1')
    assert response.status_code == 503


@pytest.mark.unit
def test_get_phase_audio_returns_401_when_unauthenticated() -> None:
    """GET /audio/{phase} must return 401 without auth."""
    client = TestClient(_build_test_app())
    response = client.get('/api/sessions/session-abc/audio/1')
    assert response.status_code == 401
