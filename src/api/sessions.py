"""Session route handlers — thin wrappers around session_service."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth_dependencies import get_current_user
from src.lib.session_service import (
    complete_session,
    fetch_session_detail,
    fetch_session_history,
    start_session,
    update_user_profile,
)
from src.types.session import (
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionDetail,
    SessionHistoryItem,
    SessionStartRequest,
    SessionStartResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix='/api/sessions', tags=['sessions'])
users_router = APIRouter(prefix='/api/users', tags=['users'])
logger = logging.getLogger(__name__)


@router.post('/start', response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start(
    payload: SessionStartRequest,
    current_user: dict = Depends(get_current_user),
) -> SessionStartResponse:
    """Generate a new AI session script and persist it."""
    user_id: str = current_user['id']
    try:
        return await start_session(user_id, payload)
    except RuntimeError as exc:
        logger.error('session generation failed user_id=%s: %s', user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Session generation failed. Please try again.',
        ) from exc


@router.post('/complete', response_model=SessionCompleteResponse)
async def complete(
    payload: SessionCompleteRequest,
    current_user: dict = Depends(get_current_user),
) -> SessionCompleteResponse:
    """Mark a session complete and compute the mood delta."""
    user_id: str = current_user['id']
    try:
        return await complete_session(user_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get('/history', response_model=list[SessionHistoryItem])
async def history(
    current_user: dict = Depends(get_current_user),
) -> list[SessionHistoryItem]:
    """Return completed sessions for the authenticated user, newest first."""
    user_id: str = current_user['id']
    return await fetch_session_history(user_id)


@router.get('/{session_id}', response_model=SessionDetail)
async def detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionDetail:
    """Return the full session detail including script phases (for Replay)."""
    user_id: str = current_user['id']
    try:
        return await fetch_session_detail(user_id, session_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@users_router.patch('/me', status_code=status.HTTP_200_OK)
async def patch_me(
    payload: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Partially update the authenticated user's profile fields."""
    user_id: str = current_user['id']
    await update_user_profile(user_id, payload)
    return {'updated': True}
