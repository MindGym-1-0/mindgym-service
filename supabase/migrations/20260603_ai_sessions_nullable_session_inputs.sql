-- Onboarding sessions are generated without session inputs (current_feeling,
-- desired_feeling, time_available). Make these nullable so onboarding sessions
-- can be inserted without fake defaults.
ALTER TABLE ai_sessions
  ALTER COLUMN current_feeling DROP NOT NULL,
  ALTER COLUMN desired_feeling DROP NOT NULL,
  ALTER COLUMN time_available DROP NOT NULL;
