-- Drop anxiety_level from the users table.
-- Per-session anxiety is now tracked via anxiety_level_before / anxiety_level_after
-- on ai_sessions. The stored profile baseline is no longer needed.

ALTER TABLE public.users DROP COLUMN IF EXISTS anxiety_level;
