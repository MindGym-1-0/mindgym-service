-- ==========================================
-- 1. CREATE CUSTOM ENUMS
-- ==========================================
CREATE TYPE action_routing_type AS ENUM (
    'run_session', 
    'follow_up', 
    'add_applications', 
    'reach_out', 
    'research_company', 
    'prepare_questions', 
    'log_debrief', 
    'review_week'
);

-- ==========================================
-- 2. CREATE DAILY FOCUS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS public.daily_focus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    action_1_text TEXT NOT NULL,
    action_1_type action_routing_type NOT NULL,
    action_1_completed BOOLEAN NOT NULL DEFAULT FALSE,
    action_2_text TEXT,
    action_2_type action_routing_type,
    action_2_completed BOOLEAN NOT NULL DEFAULT FALSE,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Enforce unique focus logs per user per day
    CONSTRAINT unique_user_daily_focus UNIQUE (user_id, date)
);

-- ==========================================
-- 3. CREATE WEEKLY MISSION TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS public.weekly_mission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    action_1 TEXT NOT NULL,
    action_1_completed BOOLEAN NOT NULL DEFAULT FALSE,
    action_2 TEXT NOT NULL,
    action_2_completed BOOLEAN NOT NULL DEFAULT FALSE,
    action_3 TEXT NOT NULL,
    action_3_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completion_count INT NOT NULL DEFAULT 0 CHECK (completion_count BETWEEN 0 AND 3),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Enforce unique weekly tracking limits per user
    CONSTRAINT unique_user_weekly_mission UNIQUE (user_id, week_start_date)
);

-- ==========================================
-- 4. ENABLE ROW-LEVEL SECURITY (RLS)
-- ==========================================
ALTER TABLE public.daily_focus ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_mission ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- 5. DEFINE ISOLATED RLS ACCESS POLICIES
-- ==========================================

-- Daily Focus Policies
CREATE POLICY "Users can manage their own daily focus records" 
    ON public.daily_focus
    FOR ALL 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Weekly Mission Policies
CREATE POLICY "Users can manage their own weekly mission records" 
    ON public.weekly_mission
    FOR ALL 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ==========================================
-- 6. AUTOMATED PERFORMANCE TRIGGER UTILITIES
-- ==========================================

-- Auto-update calculation engine for weekly completion counts
CREATE OR REPLACE FUNCTION public.calculate_weekly_completion_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.completion_count := 
        (CASE WHEN NEW.action_1_completed THEN 1 ELSE 0 END) +
        (CASE WHEN NEW.action_2_completed THEN 1 ELSE 0 END) +
        (CASE WHEN NEW.action_3_completed THEN 1 ELSE 0 END);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_weekly_completion_count
    BEFORE INSERT OR UPDATE ON public.weekly_mission
    FOR EACH ROW
    EXECUTE FUNCTION public.calculate_weekly_completion_count();
