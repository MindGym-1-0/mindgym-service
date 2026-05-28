-- Rename score columns on ai_sessions to match agreed naming convention.
-- pre_score  → anxiety_level_before
-- post_score → anxiety_level_after
-- mood_delta → anxiety_level_delta
--
-- PostgreSQL automatically updates CHECK constraint expressions on RENAME COLUMN.

ALTER TABLE public.ai_sessions RENAME COLUMN pre_score  TO anxiety_level_before;
ALTER TABLE public.ai_sessions RENAME COLUMN post_score TO anxiety_level_after;
ALTER TABLE public.ai_sessions RENAME COLUMN mood_delta TO anxiety_level_delta;
