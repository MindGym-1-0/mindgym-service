-- =============================================================
-- Add subscription tier support to users table
-- =============================================================

-- Add subscription columns to users table
alter table public.users
add column if not exists subscription_tier text not null default 'free' check (subscription_tier in ('free', 'pro', 'premium')),
add column if not exists subscription_started_at timestamptz not null default now(),
add column if not exists subscription_renewal_at timestamptz,
add column if not exists subscription_canceled_at timestamptz;

-- Create index for querying users by tier (useful for analytics)
create index if not exists users_subscription_tier_idx on public.users (subscription_tier);

-- =============================================================
-- Create subscription_usage table to track feature usage
-- =============================================================

create table if not exists public.subscription_usage (
    -- Surrogate primary key
    id              uuid        not null default gen_random_uuid(),

    -- User who owns this usage record
    user_id         uuid        not null references public.users (id) on delete cascade,

    -- Year and month this usage is for (e.g., '2026-06')
    period          text        not null,

    -- Number of sessions completed in this billing period
    sessions_used   integer     not null default 0 check (sessions_used >= 0),

    -- Number of interviews tracked in this billing period
    interviews_used integer     not null default 0 check (interviews_used >= 0),

    -- When this record was created/last updated
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    constraint subscription_usage_pkey primary key (id),
    constraint subscription_usage_unique_user_period unique (user_id, period)
);

-- Index for efficient lookup of current period usage
create index if not exists subscription_usage_user_period_idx on public.subscription_usage (user_id, period);
