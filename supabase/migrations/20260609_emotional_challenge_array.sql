-- Change emotional_challenge from single text (with CHECK) to text[]
-- so users can select up to 2 emotional challenges during onboarding.

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_emotional_challenge_check;

ALTER TABLE users
    ALTER COLUMN emotional_challenge TYPE text[]
    USING ARRAY[emotional_challenge];
