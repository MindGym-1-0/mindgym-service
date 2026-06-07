"""Session route handlers — thin wrappers around session_service."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.lib.auth_dependencies import get_current_user
from src.lib.config import get_settings
from src.lib.elevenlabs_service import ElevenLabsError, prepare_tts_text, stream_phase_audio
from src.lib.session_service import (
    complete_session,
    fetch_phase_text,
    fetch_session_detail,
    fetch_session_history,
    start_session,
)
from src.types.session import (
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionDetail,
    SessionHistoryItem,
    SessionStartRequest,
    SessionStartResponse,
)

router = APIRouter(prefix='/api/sessions', tags=['sessions'])
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


@router.get('/{session_id}/audio/{phase}')
async def get_phase_audio(
    session_id: str,
    phase: int,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream ElevenLabs TTS audio for one phase of a session.

    Eagerly starts the generator before committing to a 200 so ElevenLabs
    failures return a proper 503 rather than a truncated stream.
    """
    if phase < 1 or phase > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Phase must be between 1 and 5.',
        )

    user_id: str = current_user['id']

    try:
        text = await fetch_phase_text(user_id, session_id, phase)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Audio generation is not configured.',
        )

    prepared = prepare_tts_text(text)
    gen = stream_phase_audio(prepared)

    try:
        first_chunk = await gen.__anext__()
    except StopAsyncIteration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Phase audio returned no data.',
        )
    except ElevenLabsError as exc:
        logger.error('ElevenLabs failed session_id=%s phase=%d: %s', session_id, phase, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Audio generation failed. Continue with the text session.',
        ) from exc

    async def _stream():
        yield first_chunk
        async for chunk in gen:
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type='audio/mpeg',
        headers={'Cache-Control': 'no-store'},
    )


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
