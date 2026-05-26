-- =============================================================
-- MIGRATION: jobs table — add last_moved_at and outcome columns
-- =============================================================

alter table public.jobs
    add column if not exists last_moved_at timestamptz not null default now();

alter table public.jobs
    add column if not exists outcome text check (outcome in ('rejected', 'offer', 'ghosted', 'withdrawn'));
