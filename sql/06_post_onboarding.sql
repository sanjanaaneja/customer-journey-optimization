-- post-onboarding behavior by channel (completers only)
-- do some channels bring in better long-term customers?

SELECT
    acquisition_channel,
    COUNT(*) AS completers,
    ROUND(AVG(transactions_90d), 1) AS avg_transactions_90d,
    ROUND(AVG(avg_balance_90d_eur), 2) AS avg_balance_eur,
    ROUND(AVG(nps_score), 1) AS avg_nps
FROM onboarding_funnel
WHERE completed_onboarding = 1
GROUP BY acquisition_channel
ORDER BY avg_nps DESC;
