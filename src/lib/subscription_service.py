"""Subscription tier service for feature access and usage tracking."""

import logging
from datetime import datetime, date
from src.types.subscription import (
    SubscriptionTier,
    UserSubscription,
    SubscriptionResponse,
    get_tier_features,
)
from src.lib.supabase_client import get_supabase_client, get_supabase_admin_client

logger = logging.getLogger(__name__)


async def get_user_subscription(user_id: str) -> UserSubscription:
    """Get the current subscription tier for a user.

    Args:
        user_id: The user's ID

    Returns:
        UserSubscription object with current tier info
    """
    supabase = get_supabase_client()

    try:
        response = supabase.table('users').select(
            'subscription_tier, subscription_started_at, subscription_renewal_at, subscription_canceled_at'
        ).eq('id', user_id).single().execute()

        if not response.data:
            # Default to free tier if not found (shouldn't happen for valid users)
            return UserSubscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
            )

        data = response.data
        return UserSubscription(
            user_id=user_id,
            tier=SubscriptionTier(data.get('subscription_tier', 'free')),
            started_at=datetime.fromisoformat(data['subscription_started_at']) if data.get('subscription_started_at') else None,
            renewal_at=datetime.fromisoformat(data['subscription_renewal_at']) if data.get('subscription_renewal_at') else None,
            canceled_at=datetime.fromisoformat(data['subscription_canceled_at']) if data.get('subscription_canceled_at') else None,
        )
    except Exception as e:
        logger.error("Error fetching subscription for user %s: %s", user_id, e)
        # Default to free tier on error
        return UserSubscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
        )


async def get_subscription_response(user_id: str) -> SubscriptionResponse:
    """Get subscription info with features and usage for a user.

    Args:
        user_id: The user's ID

    Returns:
        SubscriptionResponse with tier, features, and usage
    """
    subscription = await get_user_subscription(user_id)
    features = get_tier_features(subscription.tier)
    usage = await get_current_usage(user_id)

    return SubscriptionResponse(
        subscription=subscription,
        features=features,
        usage=usage,
    )


async def get_current_usage(user_id: str) -> dict:
    """Get current month's usage for a user.

    Args:
        user_id: The user's ID

    Returns:
        Dictionary with usage metrics for current billing period
    """
    supabase = get_supabase_client()
    current_period = date.today().strftime('%Y-%m')

    try:
        response = supabase.table('subscription_usage').select(
            'sessions_used, interviews_used'
        ).eq('user_id', user_id).eq('period', current_period).single().execute()

        if response.data:
            return {
                'sessions_used_this_month': response.data.get('sessions_used', 0),
                'interviews_used_this_month': response.data.get('interviews_used', 0),
                'billing_period': current_period,
            }

        # No usage record yet this month
        return {
            'sessions_used_this_month': 0,
            'interviews_used_this_month': 0,
            'billing_period': current_period,
        }
    except Exception as e:
        logger.warning("Could not fetch usage for user %s, period %s: %s", user_id, current_period, e)
        return {
            'sessions_used_this_month': 0,
            'interviews_used_this_month': 0,
            'billing_period': current_period,
        }


async def can_create_session(user_id: str) -> tuple[bool, str | None]:
    """Check if user can create another session based on tier limits.

    Returns:
        Tuple of (allowed: bool, error_message: str | None)
    """
    subscription = await get_user_subscription(user_id)
    features = get_tier_features(subscription.tier)

    # If unlimited sessions, always allow
    if features.sessions_per_month is None:
        return True, None

    usage = await get_current_usage(user_id)
    sessions_used = usage.get('sessions_used_this_month', 0)

    if sessions_used >= features.sessions_per_month:
        return False, (
            f"You've reached your limit of {features.sessions_per_month} sessions per month. "
            "Upgrade to Pro to get unlimited sessions."
        )

    return True, None


async def can_create_interview(user_id: str) -> tuple[bool, str | None]:
    """Check if user can create/track another interview based on tier limits.

    Returns:
        Tuple of (allowed: bool, error_message: str | None)
    """
    subscription = await get_user_subscription(user_id)
    features = get_tier_features(subscription.tier)

    # If unlimited interviews, always allow
    if features.max_interviews_tracked is None:
        return True, None

    usage = await get_current_usage(user_id)
    interviews_used = usage.get('interviews_used_this_month', 0)

    if interviews_used >= features.max_interviews_tracked:
        return False, (
            f"You've reached your limit of {features.max_interviews_tracked} interview(s) you can track. "
            f"Upgrade to Pro to track unlimited interviews."
        )

    return True, None


async def increment_session_usage(user_id: str) -> None:
    """Increment session usage for current billing period.

    Uses PostgreSQL stored procedure for atomic, race-condition-safe increment.

    Args:
        user_id: The user's ID
    """
    supabase = get_supabase_client()
    current_period = date.today().strftime('%Y-%m')

    try:
        supabase.rpc('increment_session_usage', {
            'p_user_id': user_id,
            'p_period': current_period,
        }).execute()
    except Exception as e:
        logger.error("Error incrementing session usage for user %s: %s", user_id, e)


async def increment_interview_usage(user_id: str) -> None:
    """Increment interview usage for current billing period.

    Uses PostgreSQL stored procedure for atomic, race-condition-safe increment.

    Args:
        user_id: The user's ID
    """
    supabase = get_supabase_client()
    current_period = date.today().strftime('%Y-%m')

    try:
        supabase.rpc('increment_interview_usage', {
            'p_user_id': user_id,
            'p_period': current_period,
        }).execute()
    except Exception as e:
        logger.error("Error incrementing interview usage for user %s: %s", user_id, e)


async def set_subscription_tier(user_id: str, tier: SubscriptionTier) -> bool:
    """Update a user's subscription tier (admin operation).

    Args:
        user_id: The user's ID
        tier: New subscription tier

    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_admin_client()
    if not supabase:
        logger.error("Admin client unavailable for subscription update")
        return False

    try:
        now = datetime.now().isoformat()
        update_data = {
            'subscription_tier': tier.value,
            'subscription_renewal_at': None,  # Will be set by payment processor
            'subscription_canceled_at': None,
        }
        # Only set started_at when upgrading to a paid tier
        if tier != SubscriptionTier.FREE:
            update_data['subscription_started_at'] = now
        supabase.table('users').update(update_data).eq('id', user_id).execute()
        return True
    except Exception as e:
        logger.error("Error updating subscription tier for user %s: %s", user_id, e)
        return False
