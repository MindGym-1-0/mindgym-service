-- =============================================================
-- MIGRATION: interviews table - add post-interview check-in fields
-- =============================================================

alter table public.interviews
    add column if not exists outcome text;

alter table public.interviews
    add column if not exists check_in_attempts integer;

alter table public.interviews
    add column if not exists next_checkin_at timestamptz;

alter table public.interviews
    alter column outcome set default 'pending';

alter table public.interviews
    alter column check_in_attempts set default 0;

update public.interviews
set outcome = 'pending'
where outcome is null;

update public.interviews
set check_in_attempts = 0
where check_in_attempts is null;

alter table public.interviews
    alter column outcome set not null;

alter table public.interviews
    alter column check_in_attempts set not null;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'interviews_outcome_check'
          and conrelid = 'public.interviews'::regclass
    ) then
        alter table public.interviews
            add constraint interviews_outcome_check
            check (outcome in ('offer', 'no_offer', 'awaiting', 'pending'));
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'interviews_check_in_attempts_check'
          and conrelid = 'public.interviews'::regclass
    ) then
        alter table public.interviews
            add constraint interviews_check_in_attempts_check
            check (check_in_attempts >= 0);
    end if;
end
$$;
