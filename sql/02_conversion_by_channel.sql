-- conversion rate per acquisition channel
-- which channels bring in prospects that actually finish?

SELECT
    acquisition_channel,
    COUNT(*) AS total_prospects,
    SUM(completed_onboarding) AS completions,
    ROUND(100.0 * SUM(completed_onboarding) / COUNT(*), 2) AS conversion_rate_pct
FROM onboarding_funnel
GROUP BY acquisition_channel
ORDER BY conversion_rate_pct DESC;
