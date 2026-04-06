-- overall funnel shape
-- how many prospects reach each step and what's the final conversion?

SELECT
    COUNT(*) AS total_prospects,
    SUM(reached_step_1) AS step_1,
    SUM(reached_step_2) AS step_2,
    SUM(reached_step_3) AS step_3,
    SUM(reached_step_4) AS step_4,
    SUM(reached_step_5) AS step_5,
    SUM(reached_step_6) AS step_6,
    SUM(completed_onboarding) AS completed,
    ROUND(100.0 * SUM(completed_onboarding) / COUNT(*), 2) AS conversion_rate_pct
FROM onboarding_funnel;
