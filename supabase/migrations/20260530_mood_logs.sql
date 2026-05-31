-- supabase/migrations/006_mood_logs.sql

CREATE TABLE IF NOT EXISTS public.mood_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    score INT NOT NULL CONSTRAINT chk_score_range CHECK (score >= 1 AND score <= 10),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast user summary aggregations
CREATE INDEX IF NOT EXISTS idx_mood_logs_user_date ON public.mood_logs (user_id, created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.mood_logs ENABLE ROW LEVEL SECURITY;

-- Policy 1: Allow users to view only their own mood logs
CREATE POLICY "Users can view their own mood logs" 
ON public.mood_logs
FOR SELECT 
TO authenticated
USING (auth.uid() = user_id);

-- Policy 2: Allow users to insert only their own mood logs
CREATE POLICY "Users can insert their own mood logs" 
ON public.mood_logs
FOR INSERT 
TO authenticated
WITH CHECK (auth.uid() = user_id);
