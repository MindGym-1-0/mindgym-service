"""Session service — orchestrates session generation and completion."""
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import HTTPException

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

logger = logging.getLogger(__name__)


async def _ensure_user_profile(user_id: str) -> None:
    """Upsert a minimal users row so the ai_sessions FK is never violated.

    Uses ignore_duplicates=True so existing rows are untouched — only missing rows
    get created. Required for users created before the signup fix was deployed.
    """
    client = get_supabase_admin_client()
    if client is None:
        return
    try:
        await asyncio.to_thread(
            lambda: client.table("users")
            .upsert(
                {
                    "id": user_id,
                    "goal": "",
                    "stage": "exploring",
                    "anxiety_level": 5,
                },
                on_conflict="id",
                ignore_duplicates=True,
            )
            .execute()
        )
    except Exception:
        logger.warning(
            "Failed to ensure users row for user_id=%s — session insert may fail", user_id
        )


async def insert_session(user_id: str, request: SessionStartRequest, script: SessionScript) -> str | None:
    """Insert a new ai_sessions row and return the generated session id."""
    await _ensure_user_profile(user_id)
    client = get_supabase_admin_client()
    payload = {
        'user_id': user_id,
        'preparation_for': request.preparation_for,
        'current_feeling': request.current_feeling,
        'desired_feeling': request.desired_feeling,
        'time_available': request.time_available,
        'company': request.company,
        'role': request.role,
        'feeling_note': request.feeling_note,
        'anxiety_level_before': request.anxiety_level_before,
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
        .select('id, user_id, anxiety_level_before, completed_at')
        .eq('id', session_id)
        .maybe_single()
        .execute()
    )
    return getattr(result, 'data', None) or None


async def update_session(session_id: str, anxiety_level_after: int, anxiety_level_delta: int) -> None:
    """Update an ai_sessions row with anxiety_level_after, anxiety_level_delta, and completed_at."""
    client = get_supabase_admin_client()
    result = await asyncio.to_thread(
        lambda: client.table('ai_sessions')
        .update({
            'anxiety_level_after': anxiety_level_after,
            'anxiety_level_delta': anxiety_level_delta,
            'completed_at': datetime.now(timezone.utc).isoformat(),
        })
        .eq('id', session_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError(f'Failed to update session {session_id!r} — no rows matched.')


async def _fetch_user_context(user_id: str) -> dict | None:
    """Fetch onboarding fields for personalising the session prompt.

    Returns None on any failure — session generation continues without context.
    """
    client = get_supabase_admin_client()
    if client is None:
        return None
    try:
        result = await asyncio.to_thread(
            lambda: client.table("users")
            .select("employment_status, unemployed_duration, emotional_challenge, target_role_note, baseline_anxiety")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return getattr(result, "data", None) or None
    except Exception:
        logger.warning("Failed to fetch user context for user_id=%s — session will proceed without it", user_id)
        return None


async def start_session(user_id: str, request: SessionStartRequest) -> SessionStartResponse:
    """Orchestrate session generation — call Gemini, fall back if needed, persist, return.

    Raises RuntimeError if both Gemini and the fallback fail, or if the DB insert returns no id.
    """
    import time
    _t0 = time.monotonic()

    user_context = await _fetch_user_context(user_id)

    try:
        script = await asyncio.wait_for(
            asyncio.to_thread(
                generate_script,
                preparation_for=request.preparation_for,
                current_feeling=request.current_feeling,
                desired_feeling=request.desired_feeling,
                time_available=request.time_available,
                anxiety_level_before=request.anxiety_level_before,
                company=request.company,
                role=request.role,
                feeling_note=request.feeling_note,
                user_context=user_context,
            ),
            timeout=30.0,
        )
        logger.info("Gemini completed in %.1fs", time.monotonic() - _t0)
    except asyncio.TimeoutError:
        logger.warning("Gemini timed out after %.1fs — using fallback", time.monotonic() - _t0)
        script = None

    if script is None:
        try:
            script = get_fallback_script(
                preparation_for=request.preparation_for,
                company=request.company,
                role=request.role,
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
        .select('id, preparation_for, anxiety_level_before, anxiety_level_after, anxiety_level_delta, completed_at, created_at')
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
            'company, role, feeling_note, anxiety_level_before, anxiety_level_after, anxiety_level_delta, '
            'phase1, phase2, phase3, phase4, phase5, '
            'completed_at, created_at, user_id'
        )
        .eq('id', session_id)
        .maybe_single()
        .execute()
    )
    row = getattr(result, 'data', None)
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
        'feeling_note': row.get('feeling_note'),
        'anxiety_level_before': row['anxiety_level_before'],
        'anxiety_level_after': row.get('anxiety_level_after'),
        'anxiety_level_delta': row.get('anxiety_level_delta'),
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
    """Mark a session complete, compute anxiety_level_delta, and persist.

    Raises LookupError if the session does not exist or belongs to another user.
    """
    session = await fetch_session(request.session_id)

    if session is None:
        raise LookupError(f'Session {request.session_id!r} not found.')

    if session.get('user_id') and session['user_id'] != user_id:
        raise LookupError(f'Session {request.session_id!r} not found.')

    anxiety_level_before = session['anxiety_level_before']
    anxiety_level_delta = request.anxiety_level_after - anxiety_level_before

    await update_session(request.session_id, request.anxiety_level_after, anxiety_level_delta)

    return SessionCompleteResponse(
        session_id=request.session_id,
        anxiety_level_before=anxiety_level_before,
        anxiety_level_after=request.anxiety_level_after,
        anxiety_level_delta=anxiety_level_delta,
        message=f'Session complete. Anxiety shifted by {anxiety_level_delta:+d}.',
    )


async def insert_onboarding_session(
    user_id: str,
    preparation_for: str,
    baseline_anxiety: int,
    script: SessionScript,
) -> str | None:
    """Insert the first session created during onboarding."""
    await _ensure_user_profile(user_id)
    client = get_supabase_admin_client()
    payload = {
        'user_id': user_id,
        'preparation_for': preparation_for,
        'anxiety_level_before': baseline_anxiety,
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
        raise HTTPException(
            status_code=500,
            detail="Failed to save session, please retry.",
        )
    return result.data[0].get('id')
