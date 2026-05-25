-- Step 1: Drop the check constraint first
ALTER TABLE public.users 
    DROP CONSTRAINT IF EXISTS users_anxiety_level_check;

-- Step 2: Rename the column
ALTER TABLE public.users 
    RENAME COLUMN anxiety_level TO mood;

-- Step 3: Change type and drop not null
ALTER TABLE public.users 
    ALTER COLUMN mood TYPE text USING mood::text,
    ALTER COLUMN mood DROP NOT NULL;
