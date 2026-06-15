"""Subscription tier management endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth_dependencies import get_current_user
from src.lib.subscription_service import get_subscription_response
from src.types.subscription import SubscriptionResponse, TIER_FEATURES

router = APIRouter(prefix='/api/subscriptions', tags=['subscriptions'])
logger = logging.getLogger(__name__)


@router.get('/me', response_model=SubscriptionResponse, status_code=status.HTTP_200_OK)
async def get_my_subscription(
    current_user: dict = Depends(get_current_user),
) -> SubscriptionResponse:
    """Get current user's subscription tier, features, and usage.

    Returns:
        SubscriptionResponse with current tier, available features, and monthly usage
    """
    user_id: str = current_user['id']
    try:
        return await get_subscription_response(user_id)
    except Exception as exc:
        logger.error('get_my_subscription: failed for user %s — %s', user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not fetch subscription information.',
        ) from exc


@router.get('/tiers', response_model=dict, status_code=status.HTTP_200_OK)
async def get_available_tiers() -> dict:
    """Get all available subscription tiers with features.

    This is a public endpoint (no auth required) to show pricing and features.

    Returns:
        Dictionary with tier information organized by tier name
    """
    return {
        tier.value: {
            'name': features.name,
            'price_cents': features.price_cents,
            'price_display': f'${features.price_cents / 100:.2f}' if features.price_cents > 0 else 'Free',
            'features': {
                'sessions_per_month': features.sessions_per_month,
                'max_interviews_tracked': features.max_interviews_tracked,
                'full_insights_trends': features.full_insights_trends,
                'coach_notes_history': features.coach_notes_history,
                'human_coach_calls': features.human_coach_calls,
                'custom_session_packs': features.custom_session_packs,
                'basic_mood_tracking': features.basic_mood_tracking,
            }
        }
        for tier, features in TIER_FEATURES.items()
    }
