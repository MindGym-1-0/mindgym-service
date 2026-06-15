"""Subscription tier types and models."""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Available subscription tiers."""

    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class SubscriptionTierFeatures(BaseModel):
    """Feature limits for each subscription tier."""

    tier: SubscriptionTier
    name: str
    price_cents: int  # Price in cents (e.g., 1200 = $12.00)
    sessions_per_month: int | None = None  # None = unlimited
    max_interviews_tracked: int | None = None  # None = unlimited
    full_insights_trends: bool = False
    coach_notes_history: bool = False
    basic_mood_tracking: bool = False


# Tier feature configurations
TIER_FEATURES: dict[SubscriptionTier, SubscriptionTierFeatures] = {
    SubscriptionTier.FREE: SubscriptionTierFeatures(
        tier=SubscriptionTier.FREE,
        name="Free",
        price_cents=0,
        sessions_per_month=3,
        max_interviews_tracked=1,
        basic_mood_tracking=True,
    ),
    SubscriptionTier.PRO: SubscriptionTierFeatures(
        tier=SubscriptionTier.PRO,
        name="Pro",
        price_cents=1200,  # $12/month
        sessions_per_month=None,  # unlimited
        max_interviews_tracked=None,  # unlimited
        full_insights_trends=True,
        coach_notes_history=True,
        basic_mood_tracking=True,
    ),
    SubscriptionTier.PREMIUM: SubscriptionTierFeatures(
        tier=SubscriptionTier.PREMIUM,
        name="Premium",
        price_cents=2400,  # $24/month
        sessions_per_month=None,  # unlimited
        max_interviews_tracked=None,  # unlimited
        full_insights_trends=True,
        coach_notes_history=True,
        basic_mood_tracking=True,
    ),
}


class UserSubscription(BaseModel):
    """Current subscription info for a user."""

    user_id: str
    tier: SubscriptionTier
    started_at: datetime | None = None  # When paid subscription started (None for free tier users)
    renewal_at: datetime | None = None  # When the current billing period ends
    canceled_at: datetime | None = None  # When subscription was canceled


class SubscriptionResponse(BaseModel):
    """Response with subscription info and remaining usage."""

    subscription: UserSubscription
    features: SubscriptionTierFeatures
    usage: dict = Field(
        default_factory=dict,
        description="Current usage metrics (e.g., sessions_used_this_month: 2)",
    )


def get_tier_features(tier: SubscriptionTier) -> SubscriptionTierFeatures:
    """Get feature configuration for a subscription tier."""
    return TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])
