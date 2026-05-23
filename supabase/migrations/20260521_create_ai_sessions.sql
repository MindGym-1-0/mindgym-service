-- =============================================================
-- TABLE: ai_sessions
-- Stores AI-generated visualization sessions per user.
-- Separate from user_sessions (shared meditation catalogue).
-- =============================================================

create table if not exists public.ai_sessions (
    -- Surrogate primary key
    id                  uuid        not null default gen_random_uuid(),

    -- User who started the session
    user_id             uuid        not null references public.users (id) on delete cascade,

    -- What the user is preparing for
    preparation_for     text        not null check (preparation_for in (
                            'interview_tomorrow', 'recruiter_call', 'networking', 'salary_negotiation',
                            'rejection_recovery', 'restarting_search', 'general_reset'
                        )),

    -- Optional: company and role personalise phase3 and phase5 when provided
    company             text,
    role                text,

    -- How the user feels going in and what they want to feel after
    current_feeling     text        not null,
    desired_feeling     text        not null,

    -- Time the user has available for the session; constrained to Figma dropdown values
    time_available      text        not null check (time_available in ('5 min', '10 min', '15 min')),

    -- Mood score before the session (1–10)
    pre_score           smallint    not null check (pre_score between 1 and 10),

    -- Mood score after the session (1–10); set on completion
    post_score          smallint    check (post_score between 1 and 10),

    -- post_score minus pre_score; set on completion; constrained to match the two scores
    mood_delta          smallint    check (mood_delta = post_score - pre_score),

    -- The 5-phase AI-generated script
    phase1              text,
    phase2              text,
    phase3              text,
    phase4              text,
    phase5              text,

    -- When the session was completed; null until POST /api/sessions/complete
    completed_at        timestamptz,

    -- Row creation timestamp
    created_at          timestamptz not null default now(),

    constraint ai_sessions_pkey primary key (id)
);

-- Fetch a user's sessions ordered by most recent
create index if not exists ai_sessions_user_id_created_at_idx on public.ai_sessions (user_id, created_at desc);

-- =============================================================
-- ROW LEVEL SECURITY
-- =============================================================

alter table public.ai_sessions enable row level security;

-- ai_sessions: own rows only
create policy "ai_sessions: own rows"
    on public.ai_sessions for all
    using      ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
