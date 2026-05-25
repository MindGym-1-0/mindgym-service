"""Session service — orchestrates session generation and completion."""
import asyncio
from datetime import datetime, timezone

from src.lib.fallbacks import get_fallback_script
from src.lib.gemini_service import generate_script
from src.lib.supabase_client import get_supabase_admin_client
from src.types.session import (
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionScript,
    SessionStartRequest,
    SessionStartResponse,
)

_USER_CONTEXT_DEFAULTS = {'goal': '', 'stage': '', 'anxiety_level': 5}


async def fetch_user_context(user_id: str) -> dict:
    """Fetch goal, stage, and anxiety_level from the users table."""
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('users')
        .select('goal, stage, anxiety_level')
        .eq('id', user_id)
        .maybe_single()
        .execute()
    )
    return result.data or {}


async def insert_session(user_id: str, request: SessionStartRequest, script: SessionScript) -> str | None:
    """Insert a new ai_sessions row and return the generated session id."""
    client = get_supabase_admin_client()
    payload = {
        'user_id': user_id,
        'preparation_for': request.preparation_for,
        'current_feeling': request.current_feeling,
        'desired_feeling': request.desired_feeling,
        'time_available': request.time_available,
        'company': request.company,
        'role': request.role,
        'pre_score': request.pre_score,
        'phase1': script.phase1,
        'phase2': script.phase2,
        'phase3': script.phase3,
        'phase4': script.phase4,
        'phase5': script.phase5,
    }
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions').insert(payload).execute()
    )
    if not result.data:
        return None
    return result.data[0].get('id')


async def fetch_session(session_id: str) -> dict | None:
    """Fetch an ai_sessions row by id."""
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions')
        .select('id, user_id, pre_score, completed_at')
        .eq('id', session_id)
        .maybe_single()
        .execute()
    )
    return result.data or None


async def update_session(session_id: str, post_score: int, mood_delta: int) -> None:
    """Update an ai_sessions row with post_score, mood_delta, and completed_at."""
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions')
        .update({
            'post_score': post_score,
            'mood_delta': mood_delta,
            'completed_at': datetime.now(timezone.utc).isoformat(),
        })
        .eq('id', session_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError(f'Failed to update session {session_id!r} — no rows matched.')


async def start_session(user_id: str, request: SessionStartRequest) -> SessionStartResponse:
    """Orchestrate session generation — fetch user context, call Gemini, fall back if needed, persist, return.

    Raises RuntimeError if both Gemini and the fallback fail, or if the DB insert returns no id.
    """
    raw_context = await fetch_user_context(user_id)
    user_context = {**_USER_CONTEXT_DEFAULTS, **{k: v for k, v in raw_context.items() if v is not None}}

    script = generate_script(
        preparation_for=request.preparation_for,
        current_feeling=request.current_feeling,
        desired_feeling=request.desired_feeling,
        time_available=request.time_available,
        company=request.company,
        role=request.role,
        user_context=user_context,
    )

    if script is None:
        try:
            script = get_fallback_script(
                preparation_for=request.preparation_for,
                company=request.company,
                role=request.role,
                goal=user_context.get('goal'),
            )
        except ValueError as exc:
            raise RuntimeError(f'Session generation failed and no fallback exists: {exc}') from exc

    session_id = await insert_session(user_id, request, script)
    if session_id is None:
        raise RuntimeError('Session was generated but could not be persisted — insert returned no id.')

    return SessionStartResponse(
        session_id=session_id,
        script=script,
        mode=request.preparation_for,
    )


async def fetch_session_history(user_id: str) -> list:
    """Return completed sessions for a user, ordered newest first."""
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions')
        .select('id, preparation_for, pre_score, post_score, mood_delta, completed_at, created_at')
        .eq('user_id', user_id)
        .not_.is_('completed_at', 'null')
        .order('completed_at', desc=True)
        .execute()
    )
    return result.data or []


async def fetch_session_detail(user_id: str, session_id: str) -> dict:
    """Return a full session row including script phases.

    Raises LookupError if the session does not exist or belongs to another user.
    """
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions')
        .select(
            'id, preparation_for, current_feeling, desired_feeling, time_available, '
            'company, role, pre_score, post_score, mood_delta, '
            'phase1, phase2, phase3, phase4, phase5, '
            'completed_at, created_at, user_id'
        )
        .eq('id', session_id)
        .maybe_single()
        .execute()
    )
    row = result.data
    if not row:
        raise LookupError(f'Session {session_id!r} not found.')
    if row.get('user_id') and row['user_id'] != user_id:
        raise LookupError(f'Session {session_id!r} not found.')

    return {
        'id': row['id'],
        'preparation_for': row['preparation_for'],
        'current_feeling': row['current_feeling'],
        'desired_feeling': row['desired_feeling'],
        'time_available': row['time_available'],
        'company': row.get('company'),
        'role': row.get('role'),
        'pre_score': row['pre_score'],
        'post_score': row.get('post_score'),
        'mood_delta': row.get('mood_delta'),
        'script': SessionScript(
            phase1=row['phase1'],
            phase2=row['phase2'],
            phase3=row['phase3'],
            phase4=row['phase4'],
            phase5=row['phase5'],
        ),
        'completed_at': row.get('completed_at'),
        'created_at': row['created_at'],
    }


async def update_user_profile(user_id: str, request) -> None:
    """Apply a partial update to the users row — only set fields that are not None."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        return
    client = get_supabase_admin_client()
    await asyncio.to_thread(
        lambda: client.table('users').update(updates).eq('id', user_id).execute()
    )


async def complete_session(user_id: str, request: SessionCompleteRequest) -> SessionCompleteResponse:
    """Mark a session complete, compute mood_delta, and persist.

    Raises LookupError if the session does not exist or belongs to another user.
    """
    session = await fetch_session(request.session_id)

    if session is None:
        raise LookupError(f'Session {request.session_id!r} not found.')

    if session.get('user_id') and session['user_id'] != user_id:
        raise LookupError(f'Session {request.session_id!r} not found.')

    pre_score = session['pre_score']
    mood_delta = request.post_score - pre_score

    await update_session(request.session_id, request.post_score, mood_delta)

    return SessionCompleteResponse(
        session_id=request.session_id,
        pre_score=pre_score,
        post_score=request.post_score,
        mood_delta=mood_delta,
        message=f'Session complete. Mood shifted by {mood_delta:+d}.',
    )
