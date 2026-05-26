-- =============================================================
-- TABLE: coach_prep_plans
-- Stores Maya's personalized prep plan per user/interview.
-- Ensures users see the same plan when they return.
-- =============================================================

create table if not exists public.coach_prep_plans (
    id              uuid        not null default gen_random_uuid(),
    user_id         uuid        not null references auth.users (id) on delete cascade,
    interview_id    uuid        not null references public.interviews (id) on delete cascade,
    worry_input     text        not null,
    plan            jsonb       not null,
    coach_note      text        not null,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    constraint coach_prep_plans_pkey primary key (id)
);

-- Safety updates for partially existing tables
alter table public.coach_prep_plans add column if not exists id uuid default gen_random_uuid();
alter table public.coach_prep_plans add column if not exists user_id uuid;
alter table public.coach_prep_plans add column if not exists interview_id uuid;
alter table public.coach_prep_plans add column if not exists worry_input text;
alter table public.coach_prep_plans add column if not exists plan jsonb;
alter table public.coach_prep_plans add column if not exists coach_note text;
alter table public.coach_prep_plans add column if not exists created_at timestamptz default now();
alter table public.coach_prep_plans add column if not exists updated_at timestamptz default now();

alter table public.coach_prep_plans alter column id set default gen_random_uuid();
alter table public.coach_prep_plans alter column worry_input set not null;
alter table public.coach_prep_plans alter column plan set not null;
alter table public.coach_prep_plans alter column coach_note set not null;
alter table public.coach_prep_plans alter column created_at set default now();
alter table public.coach_prep_plans alter column created_at set not null;
alter table public.coach_prep_plans alter column updated_at set default now();
alter table public.coach_prep_plans alter column updated_at set not null;

-- Add constraints safely if they do not already exist
do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'coach_prep_plans_pkey'
          and conrelid = 'public.coach_prep_plans'::regclass
    ) then
        alter table public.coach_prep_plans
            add constraint coach_prep_plans_pkey primary key (id);
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'coach_prep_plans_user_id_fkey'
          and conrelid = 'public.coach_prep_plans'::regclass
    ) then
        alter table public.coach_prep_plans
            add constraint coach_prep_plans_user_id_fkey
            foreign key (user_id) references auth.users(id) on delete cascade;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'coach_prep_plans_interview_id_fkey'
          and conrelid = 'public.coach_prep_plans'::regclass
    ) then
        alter table public.coach_prep_plans
            add constraint coach_prep_plans_interview_id_fkey
            foreign key (interview_id) references public.interviews(id) on delete cascade;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'coach_prep_plans_user_id_interview_id_key'
          and conrelid = 'public.coach_prep_plans'::regclass
    ) then
        alter table public.coach_prep_plans
            add constraint coach_prep_plans_user_id_interview_id_key
            unique (user_id, interview_id);
    end if;
end
$$;

alter table public.coach_prep_plans alter column user_id set not null;
alter table public.coach_prep_plans alter column interview_id set not null;

-- Optional read/update performance helpers
create index if not exists coach_prep_plans_user_id_idx on public.coach_prep_plans (user_id);
create index if not exists coach_prep_plans_interview_id_idx on public.coach_prep_plans (interview_id);

-- =============================================================
-- ROW LEVEL SECURITY
-- =============================================================

alter table public.coach_prep_plans enable row level security;

drop policy if exists "coach_prep_plans: own rows" on public.coach_prep_plans;
create policy "coach_prep_plans: own rows"
    on public.coach_prep_plans for all
    using      ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
