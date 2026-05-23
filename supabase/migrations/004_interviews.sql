-- 1. Create the interviews table mapping all required fields
CREATE TABLE IF NOT EXISTS public.interviews (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL, -- Nullable relationship if no linked job
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    event_type TEXT NOT NULL, -- phone_screen, hm_round, deep_dive, final_round, negotiation, networking, offer
    interview_date TIMESTAMPTZ NOT NULL,
    recovery_needed BOOLEAN DEFAULT FALSE NOT NULL, -- Defaults to false
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. Enable Row Level Security (RLS) as required
ALTER TABLE public.interviews ENABLE ROW LEVEL SECURITY;

-- 3. Add user isolation policies (Users can only read/write their own records)
CREATE POLICY "Users can view their own interviews" 
ON public.interviews 
FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own interviews" 
ON public.interviews 
FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own interviews" 
ON public.interviews 
FOR UPDATE 
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own interviews" 
ON public.interviews 
FOR DELETE 
USING (auth.uid() = user_id);