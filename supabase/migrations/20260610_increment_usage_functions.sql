-- Create stored procedures for atomic increment operations on subscription usage
-- This prevents race conditions when multiple requests try to increment concurrently

CREATE OR REPLACE FUNCTION increment_session_usage(
    p_user_id uuid,
    p_period text
)
RETURNS void AS $$
BEGIN
    INSERT INTO subscription_usage (user_id, period, sessions_used, interviews_used, updated_at)
    VALUES (p_user_id, p_period, 1, 0, now())
    ON CONFLICT (user_id, period)
    DO UPDATE SET
        sessions_used = subscription_usage.sessions_used + 1,
        updated_at = now();
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION increment_interview_usage(
    p_user_id uuid,
    p_period text
)
RETURNS void AS $$
BEGIN
    INSERT INTO subscription_usage (user_id, period, sessions_used, interviews_used, updated_at)
    VALUES (p_user_id, p_period, 0, 1, now())
    ON CONFLICT (user_id, period)
    DO UPDATE SET
        interviews_used = subscription_usage.interviews_used + 1,
        updated_at = now();
END;
$$ LANGUAGE plpgsql;
