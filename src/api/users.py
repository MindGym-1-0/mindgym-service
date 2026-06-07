"""User account route handlers."""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth_dependencies import get_current_user
from src.lib.session_service import update_user_profile
from src.lib.supabase_client import get_supabase_admin_client
from src.types.session import UserUpdateRequest

router = APIRouter(prefix='/api/users', tags=['users'])
logger = logging.getLogger(__name__)


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
