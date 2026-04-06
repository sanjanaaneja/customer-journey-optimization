-- mobile vs desktop vs tablet
-- does device type affect completion and the KYC step?

SELECT
    device,
    COUNT(*) AS total_prospects,
    SUM(completed_onboarding) AS completions,
    ROUND(100.0 * SUM(completed_onboarding) / COUNT(*), 2) AS conversion_rate_pct,
    SUM(reached_step_3) AS reached_kyc,
    ROUND(100.0 * SUM(reached_step_3) / COUNT(*), 2) AS kyc_rate_pct
FROM onboarding_funnel
GROUP BY device
ORDER BY conversion_rate_pct DESC;
