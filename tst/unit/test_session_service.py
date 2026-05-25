"""Unit tests for session_service — start_session and complete_session."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.lib.session_service import complete_session, start_session
from src.types.session import SessionCompleteRequest, SessionScript, SessionStartRequest


_USER_ID = 'user-123'

_VALID_REQUEST = SessionStartRequest(
    preparation_for='interview_tomorrow',
    current_feeling='overwhelmed',
    desired_feeling='confident',
    time_available='10 min',
    pre_score=2,
    company='Stripe',
    role='PM',
)

_VALID_REQUEST_NO_COMPANY = SessionStartRequest(
    preparation_for='general_reset',
    current_feeling='unsure',
    desired_feeling='calm',
    time_available='5 min',
    pre_score=5,
)

_MOCK_SCRIPT = SessionScript(
    phase1='Breathe.',
    phase2='Ground.',
    phase3='Picture yourself at Stripe as a PM.',
    phase4='Anchor.',
    phase5='You are ready for Stripe as a PM.',
)

_MOCK_USER_ROW = {
    'goal': 'Land a PM role',
    'stage': 'active',
    'anxiety_level': 5,
}

_MOCK_SESSION_ROW = {
    'id': 'session-abc',
    'pre_score': 2,
    'completed_at': None,
}


# ---------------------------------------------------------------------------
# start_session — Gemini success path
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session_returns_response_on_gemini_success() -> None:
    """start_session must return a SessionStartResponse when Gemini succeeds."""
    with patch('src.lib.session_service.fetch_user_context', new_callable=AsyncMock, return_value=_MOCK_USER_ROW), \
         patch('src.lib.session_service.generate_script', return_value=_MOCK_SCRIPT), \
         patch('src.lib.session_service.insert_session', new_callable=AsyncMock, return_value='session-abc'):

        response = await start_session(user_id=_USER_ID, request=_VALID_REQUEST)

    assert response.session_id == 'session-abc'
    assert response.script == _MOCK_SCRIPT
    assert response.mode == 'interview_tomorrow'


# ---------------------------------------------------------------------------
# start_session — Gemini failure → fallback
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session_uses_fallback_when_gemini_returns_none() -> None:
    """start_session must use the fallback script when Gemini returns None."""
    with patch('src.lib.session_service.fetch_user_context', new_callable=AsyncMock, return_value=_MOCK_USER_ROW), \
         patch('src.lib.session_service.generate_script', return_value=None), \
         patch('src.lib.session_service.get_fallback_script', return_value=_MOCK_SCRIPT) as mock_fallback, \
         patch('src.lib.session_service.insert_session', new_callable=AsyncMock, return_value='session-abc'):

        response = await start_session(user_id=_USER_ID, request=_VALID_REQUEST)

    mock_fallback.assert_called_once()
    assert response.script == _MOCK_SCRIPT


# ---------------------------------------------------------------------------
# start_session — user context safe defaults
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session_uses_safe_defaults_when_user_profile_missing() -> None:
    """start_session must still work when user profile fields are absent."""
    with patch('src.lib.session_service.fetch_user_context', new_callable=AsyncMock, return_value={}), \
         patch('src.lib.session_service.generate_script', return_value=_MOCK_SCRIPT), \
         patch('src.lib.session_service.insert_session', new_callable=AsyncMock, return_value='session-abc'):

        response = await start_session(user_id=_USER_ID, request=_VALID_REQUEST_NO_COMPANY)

    assert response.session_id == 'session-abc'


# ---------------------------------------------------------------------------
# start_session — fallback raises ValueError
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session_raises_when_fallback_fails() -> None:
    """start_session must raise a RuntimeError when both Gemini and fallback fail."""
    with patch('src.lib.session_service.fetch_user_context', new_callable=AsyncMock, return_value=_MOCK_USER_ROW), \
         patch('src.lib.session_service.generate_script', return_value=None), \
         patch('src.lib.session_service.get_fallback_script', side_effect=ValueError('Unknown')):

        with pytest.raises(RuntimeError):
            await start_session(user_id=_USER_ID, request=_VALID_REQUEST)


# ---------------------------------------------------------------------------
# start_session — insert failure
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session_raises_when_insert_returns_no_id() -> None:
    """start_session must raise a RuntimeError when the DB insert returns no session id."""
    with patch('src.lib.session_service.fetch_user_context', new_callable=AsyncMock, return_value=_MOCK_USER_ROW), \
         patch('src.lib.session_service.generate_script', return_value=_MOCK_SCRIPT), \
         patch('src.lib.session_service.insert_session', new_callable=AsyncMock, return_value=None):

        with pytest.raises(RuntimeError):
            await start_session(user_id=_USER_ID, request=_VALID_REQUEST)


# ---------------------------------------------------------------------------
# complete_session — success
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_session_returns_correct_mood_delta() -> None:
    """complete_session must return mood_delta = post_score - pre_score."""
    request = SessionCompleteRequest(session_id='session-abc', post_score=7)

    with patch('src.lib.session_service.fetch_session', new_callable=AsyncMock, return_value=_MOCK_SESSION_ROW), \
         patch('src.lib.session_service.update_session', new_callable=AsyncMock):

        response = await complete_session(user_id=_USER_ID, request=request)

    assert response.mood_delta == 5  # 7 - 2
    assert response.pre_score == 2
    assert response.post_score == 7


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_session_allows_negative_mood_delta() -> None:
    """complete_session must allow negative mood_delta without clamping."""
    request = SessionCompleteRequest(session_id='session-abc', post_score=1)

    with patch('src.lib.session_service.fetch_session', new_callable=AsyncMock, return_value=_MOCK_SESSION_ROW), \
         patch('src.lib.session_service.update_session', new_callable=AsyncMock):

        response = await complete_session(user_id=_USER_ID, request=request)

    assert response.mood_delta == -1  # 1 - 2


# ---------------------------------------------------------------------------
# complete_session — session not found / wrong user
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_session_raises_when_session_not_found() -> None:
    """complete_session must raise a 404-style error when session does not exist."""
    request = SessionCompleteRequest(session_id='missing-session', post_score=7)

    with patch('src.lib.session_service.fetch_session', new_callable=AsyncMock, return_value=None):

        with pytest.raises(LookupError):
            await complete_session(user_id=_USER_ID, request=request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_session_raises_404_when_session_belongs_to_other_user() -> None:
    """complete_session must raise LookupError (not PermissionError) when session belongs to another user."""
    request = SessionCompleteRequest(session_id='session-abc', post_score=7)
    other_user_session = {**_MOCK_SESSION_ROW, 'user_id': 'other-user-999'}

    with patch('src.lib.session_service.fetch_session', new_callable=AsyncMock, return_value=other_user_session):

        with pytest.raises(LookupError):
            await complete_session(user_id=_USER_ID, request=request)


# ---------------------------------------------------------------------------
# update_session — silent failure detection
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_session_raises_when_update_returns_no_rows() -> None:
    """complete_session must raise RuntimeError when the DB update matches no rows."""
    request = SessionCompleteRequest(session_id='session-abc', post_score=7)

    with patch('src.lib.session_service.fetch_session', new_callable=AsyncMock, return_value=_MOCK_SESSION_ROW), \
         patch('src.lib.session_service.update_session', new_callable=AsyncMock, side_effect=RuntimeError('no rows matched')):

        with pytest.raises(RuntimeError):
            await complete_session(user_id=_USER_ID, request=request)
