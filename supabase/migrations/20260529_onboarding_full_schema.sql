-- adding target role columns 
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS target_role_category text
    CHECK (target_role_category in ('product_design_ux', 'product_management', 'software_engineering', 'data_analytics', 'marketing', 'sales', 'operations', 'finance', 'people_hr', 'leadership_executive', 'not_sure'));

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS target_role_note text;
    
-- drop tables from the old version for comapnies
ALTER TABLE public.users DROP COLUMN IF EXISTS company_size;

-- create new company size column
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS company_types text[];
    

-- drop wrong columns from user for screen 6
ALTER TABLE public.users 
    DROP COLUMN IF EXISTS recruiter_contacts_min,
    DROP COLUMN IF EXISTS recruiter_contacts_max,
    DROP COLUMN IF EXISTS onsite_interviews_min,
    DROP COLUMN IF EXISTS onsite_interviews_max,
    DROP COLUMN IF EXISTS final_round_interviews_min,
    DROP COLUMN IF EXISTS final_round_interviews_max,
    DROP COLUMN IF EXISTS offers_min,
    DROP COLUMN IF EXISTS offers_max;

-- add columns in user for screen 6
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS recruiter_contacts integer,
    ADD COLUMN IF NOT EXISTS first_round_interviews integer,
    ADD COLUMN IF NOT EXISTS final_round_interviews integer,
    ADD COLUMN IF NOT EXISTS offers integer;

-- add emotional challenge
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS emotional_challenge text
    CHECK (emotional_challenge in ('rejection_silence', 'interview_anxiety', 'imposter_syndrome', 'burnout', 'uncertainty', 'financial_pressure'));

-- add baseline anxiety
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS baseline_anxiety integer
    CHECK (baseline_anxiety BETWEEN 1 AND 10);

-- add time onboarding complete
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz;