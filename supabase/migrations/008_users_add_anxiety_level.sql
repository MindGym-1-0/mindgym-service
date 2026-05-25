ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS anxiety_level smallint
    CHECK (anxiety_level BETWEEN 1 AND 10);