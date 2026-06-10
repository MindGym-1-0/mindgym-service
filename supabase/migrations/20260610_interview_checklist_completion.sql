-- =============================================================
-- TABLE: interview_checklist_completion
-- Persists checklist item completion per user/interview/item.
-- =============================================================

create table if not exists public.interview_checklist_completion (
    id              uuid        not null default gen_random_uuid(),
    user_id         uuid        not null references public.users (id) on delete cascade,
    interview_id    uuid        not null references public.interviews (id) on delete cascade,
    item_id         text        not null,
    checked         boolean     not null default false,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    constraint interview_checklist_completion_pkey primary key (id)
);

alter table public.interview_checklist_completion add column if not exists id uuid default gen_random_uuid();
alter table public.interview_checklist_completion add column if not exists user_id uuid;
alter table public.interview_checklist_completion add column if not exists interview_id uuid;
alter table public.interview_checklist_completion add column if not exists item_id text;
alter table public.interview_checklist_completion add column if not exists checked boolean default false;
alter table public.interview_checklist_completion add column if not exists created_at timestamptz default now();
alter table public.interview_checklist_completion add column if not exists updated_at timestamptz default now();

alter table public.interview_checklist_completion alter column id set default gen_random_uuid();
alter table public.interview_checklist_completion alter column checked set default false;
alter table public.interview_checklist_completion alter column checked set not null;
alter table public.interview_checklist_completion alter column created_at set default now();
alter table public.interview_checklist_completion alter column created_at set not null;
alter table public.interview_checklist_completion alter column updated_at set default now();
alter table public.interview_checklist_completion alter column updated_at set not null;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'interview_checklist_completion_pkey'
          and conrelid = 'public.interview_checklist_completion'::regclass
    ) then
        alter table public.interview_checklist_completion
            add constraint interview_checklist_completion_pkey primary key (id);
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'interview_checklist_completion_user_id_fkey'
          and conrelid = 'public.interview_checklist_completion'::regclass
    ) then
        alter table public.interview_checklist_completion
            add constraint interview_checklist_completion_user_id_fkey
            foreign key (user_id) references public.users(id) on delete cascade;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'interview_checklist_completion_interview_id_fkey'
          and conrelid = 'public.interview_checklist_completion'::regclass
    ) then
        alter table public.interview_checklist_completion
            add constraint interview_checklist_completion_interview_id_fkey
            foreign key (interview_id) references public.interviews(id) on delete cascade;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'interview_checklist_completion_user_id_interview_id_item_id_key'
          and conrelid = 'public.interview_checklist_completion'::regclass
    ) then
        alter table public.interview_checklist_completion
            add constraint interview_checklist_completion_user_id_interview_id_item_id_key
            unique (user_id, interview_id, item_id);
    end if;
end
$$;

alter table public.interview_checklist_completion alter column user_id set not null;
alter table public.interview_checklist_completion alter column interview_id set not null;
alter table public.interview_checklist_completion alter column item_id set not null;

create index if not exists interview_checklist_completion_user_interview_idx
    on public.interview_checklist_completion (user_id, interview_id);

alter table public.interview_checklist_completion enable row level security;

drop policy if exists "interview_checklist_completion: own rows" on public.interview_checklist_completion;
create policy "interview_checklist_completion: own rows"
    on public.interview_checklist_completion for all
    using      ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
