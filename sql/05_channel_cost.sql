-- how much does each channel cost, and what's the cost per actual conversion?
-- helps figure out which channels are worth the spend

SELECT
    acquisition_channel,
    COUNT(*) AS total_prospects,
    SUM(completed_onboarding) AS completions,
    ROUND(AVG(acquisition_cost_eur), 2) AS avg_cost_eur,
    ROUND(SUM(acquisition_cost_eur) / NULLIF(SUM(completed_onboarding), 0), 2) AS cost_per_conversion
FROM onboarding_funnel
GROUP BY acquisition_channel
ORDER BY cost_per_conversion;
