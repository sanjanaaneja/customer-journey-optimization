-- why are people dropping off?
-- only looking at those who didn't complete onboarding

SELECT
    dropout_reason,
    COUNT(*) AS dropout_count
FROM onboarding_funnel
WHERE completed_onboarding = 0
GROUP BY dropout_reason
ORDER BY dropout_count DESC;
