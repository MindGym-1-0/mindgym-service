-- Create the streaks table if it doesn't exist, using CASCADE on delete
CREATE TABLE IF NOT EXISTS public.streaks (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    current_streak INT DEFAULT 0 NOT NULL,
    longest_streak INT DEFAULT 0 NOT NULL,
    last_active DATE,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Safety checks: Add columns individually if the table existed but missed specific fields
ALTER TABLE public.streaks ADD COLUMN IF NOT EXISTS current_streak INT DEFAULT 0 NOT NULL;
ALTER TABLE public.streaks ADD COLUMN IF NOT EXISTS longest_streak INT DEFAULT 0 NOT NULL;
ALTER TABLE public.streaks ADD COLUMN IF NOT EXISTS last_active DATE;
ALTER TABLE public.streaks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL;

-- Enable Row Level Security (RLS)
ALTER TABLE public.streaks ENABLE ROW LEVEL SECURITY;

-- Unified policy matching Anastasiia's optimization pattern
DROP POLICY IF EXISTS "streaks: own rows" ON public.streaks;
CREATE POLICY "streaks: own rows"
ON public.streaks FOR ALL
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);