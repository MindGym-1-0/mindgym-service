-- 1. Create the interviews table with foreign keys and cascade delete
CREATE TABLE IF NOT EXISTS public.interviews (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE, -- Cascades delete if user is removed
    job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL, 
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    event_type TEXT NOT NULL, 
    interview_date TIMESTAMPTZ NOT NULL,
    recovery_needed BOOLEAN DEFAULT FALSE NOT NULL, 
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. Add performance index on user_id to avoid table scans
CREATE INDEX IF NOT EXISTS interviews_user_id_idx ON public.interviews (user_id);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.interviews ENABLE ROW LEVEL SECURITY;

-- 4. Single unified policy for consistency and performance optimization
CREATE POLICY "interviews: own rows"
ON public.interviews FOR ALL
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);