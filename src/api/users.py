"""User account route handlers."""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.lib.auth_dependencies import get_current_user
from src.lib.session_service import update_user_profile
from src.lib.supabase_client import get_supabase_admin_client
from src.types.session import UserUpdateRequest

router = APIRouter(prefix='/api/users', tags=['users'])
logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    mindset_gap: str | None = None
    mindset_gap_detail: str | None = None
    hunting_gap: str | None = None
    hunting_gap_detail: str | None = None
    applications_sent_min: int | None = None
    applications_sent_max: int | None = None
    recruiter_contacts: int | None = None
    first_round_interviews: int | None = None
    final_round_interviews: int | None = None
    offers: int | None = None


_ME_FIELDS = (
    'mindset_gap, mindset_gap_detail, hunting_gap, hunting_gap_detail, '
    'applications_sent_min, applications_sent_max, recruiter_contacts, '
    'first_round_interviews, final_round_interviews, offers'
)


@router.get('/me', status_code=status.HTTP_200_OK, response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserProfile:
    """Return the authenticated user's gap analysis and onboarding funnel stats."""
    user_id: str = current_user['id']
    client = get_supabase_admin_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Database client unavailable.',
        )
    try:
        result = await asyncio.to_thread(
            lambda: client.table('users')
            .select(_ME_FIELDS)
            .eq('id', user_id)
            .single()
            .execute()
        )
        row = result.data or {}
        return UserProfile(
            mindset_gap=row.get('mindset_gap'),
            mindset_gap_detail=row.get('mindset_gap_detail'),
            hunting_gap=row.get('hunting_gap'),
            hunting_gap_detail=row.get('hunting_gap_detail'),
            applications_sent_min=row.get('applications_sent_min'),
            applications_sent_max=row.get('applications_sent_max'),
            recruiter_contacts=row.get('recruiter_contacts'),
            first_round_interviews=row.get('first_round_interviews'),
            final_round_interviews=row.get('final_round_interviews'),
            offers=row.get('offers'),
        )
    except Exception as exc:
        logger.exception('get_me failed for user_id=%s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not fetch user profile.',
        ) from exc


@router.patch('/me', status_code=status.HTTP_200_OK)
async def patch_me(
    payload: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Partially update the authenticated user's profile fields."""
    user_id: str = current_user['id']
    await update_user_profile(user_id, payload)
    return {'updated': True}


@router.delete('/me', status_code=status.HTTP_200_OK)
async def delete_me(current_user: dict = Depends(get_current_user)) -> dict:
    """Permanently delete the authenticated user and all their data from Supabase Auth."""
    user_id: str = current_user['id']
    admin = get_supabase_admin_client()
    if admin is None:
        logger.error('delete_me: admin client unavailable (missing SUPABASE_SERVICE_ROLE_KEY)')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Account deletion is temporarily unavailable.',
        )
    try:
        await asyncio.to_thread(admin.auth.admin.delete_user, user_id)
    except Exception as exc:
        logger.error('delete_me: failed to delete user %s — %s', user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not delete your account. Please try again.',
        ) from exc
    return {'deleted': True}
