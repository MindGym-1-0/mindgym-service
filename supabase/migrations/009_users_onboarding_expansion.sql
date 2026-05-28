-- Q1: Employment status
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS employment_status text
    CHECK (employment_status IN ('employed', 'unemployed', 'laid_off'));

-- Q1.2: How long unemployed (only set if unemployed/laid_off)
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS unemployed_duration text
    CHECK (unemployed_duration IN ('1m', '2m', '3m', '6m', '1y'));

-- Q2: Job search timeline
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS job_timeline text
    CHECK (job_timeline IN ('3m', '6m', '12m', 'asap'));

-- Q4: Company size
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS company_size text
    CHECK (company_size IN ('small', 'medium', 'large'));

-- Q5: Job hunting activity (min/max ranges)
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS applications_sent_min integer,
    ADD COLUMN IF NOT EXISTS applications_sent_max integer,
    ADD COLUMN IF NOT EXISTS recruiter_contacts_min integer,
    ADD COLUMN IF NOT EXISTS recruiter_contacts_max integer,
    ADD COLUMN IF NOT EXISTS onsite_interviews_min integer,
    ADD COLUMN IF NOT EXISTS onsite_interviews_max integer,
    ADD COLUMN IF NOT EXISTS final_round_interviews_min integer,
    ADD COLUMN IF NOT EXISTS final_round_interviews_max integer,
    ADD COLUMN IF NOT EXISTS offers_min integer,
    ADD COLUMN IF NOT EXISTS offers_max integer;