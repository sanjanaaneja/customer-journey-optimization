# generate synthetic data for onboarding funnel analysis
# parameters calibrated against Signicat "Battle to Onboard" 2022,
# Signicat 2022 onboarding research, and industry banking benchmarks

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(777)

N = 8000

# channels and weights
channels = ['Organic Search', 'Paid Social', 'Referral Program', 'Direct', 'Affiliate', 'Branch Walk-in']
channel_weights = [0.25, 0.22, 0.12, 0.18, 0.13, 0.10]

# conversion rates for each channel (conditional on reaching previous step)
# conversion rates calibrated to Signicat 2022: 68% abandon, KYC is biggest drop
# CAC based on industry benchmarks: neobanks ~EUR 30, traditional digital ~EUR 200
channel_profiles = {
    'Organic Search':    {'step2': 0.82, 'step3': 0.85, 'step4': 0.68, 'step5': 0.80, 'step6': 0.75, 'cac': 45},
    'Paid Social':       {'step2': 0.70, 'step3': 0.75, 'step4': 0.58, 'step5': 0.72, 'step6': 0.65, 'cac': 85},
    'Referral Program':  {'step2': 0.88, 'step3': 0.90, 'step4': 0.75, 'step5': 0.85, 'step6': 0.80, 'cac': 25},
    'Direct':            {'step2': 0.78, 'step3': 0.82, 'step4': 0.65, 'step5': 0.78, 'step6': 0.70, 'cac': 20},
    'Affiliate':         {'step2': 0.68, 'step3': 0.72, 'step4': 0.55, 'step5': 0.70, 'step6': 0.60, 'cac': 60},
    'Branch Walk-in':    {'step2': 0.92, 'step3': 0.93, 'step4': 0.82, 'step5': 0.90, 'step6': 0.85, 'cac': 200},
}

STEPS = [
    'Step 1: Landing Page Visit',
    'Step 2: Account Type Selection',
    'Step 3: Personal Details Form',
    'Step 4: KYC Document Upload',
    'Step 5: Identity Verification',
    'Step 6: First Transaction'
]

# demographics
countries = ['Netherlands', 'Belgium', 'Germany', 'France', 'Spain']
country_weights = [0.30, 0.15, 0.25, 0.18, 0.12]

age_groups = ['18-24', '25-34', '35-44', '45-54', '55+']
age_weights = [0.18, 0.32, 0.25, 0.15, 0.10]

devices = ['Mobile', 'Desktop', 'Tablet']
device_weights = [0.68, 0.25, 0.07]  # Statista/EBF: 65-75% mobile banking traffic

products = ['Current Account', 'Savings Account', 'Investment Account', 'Business Account']
product_weights = [0.45, 0.25, 0.15, 0.15]

# generate the records
data = {
    'prospect_id': [f'PROS-{i:05d}' for i in range(1, N + 1)],
    'start_date': [
        datetime(2024, 1, 1) + timedelta(days=np.random.randint(0, 365))
        for _ in range(N)
    ],
    'acquisition_channel': np.random.choice(channels, N, p=channel_weights),
    'country': np.random.choice(countries, N, p=country_weights),
    'age_group': np.random.choice(age_groups, N, p=age_weights),
    'device': np.random.choice(devices, N, p=device_weights),
    'product_interest': np.random.choice(products, N, p=product_weights),
}

df = pd.DataFrame(data)

# simulate funnel - each step depends on previous one
def simulate_funnel(row):
    profile = channel_profiles[row['acquisition_channel']]

    step_rates = [1.0, profile['step2'], profile['step3'], profile['step4'], profile['step5'], profile['step6']]

    # mobile KYC completion 1.3-1.8x worse than desktop (Signicat 2022)
    if row['device'] == 'Mobile':
        step_rates[3] *= 0.78  # document upload much harder on mobile
        step_rates[4] *= 0.90
    elif row['device'] == 'Tablet':
        step_rates[3] *= 0.90

    # add some noise
    step_rates = [min(max(r + np.random.normal(0, 0.05), 0.01), 1.0) for r in step_rates]

    reached = []
    for i, rate in enumerate(step_rates):
        if i == 0:
            reached.append(1)
        else:
            if reached[i-1] == 0:
                reached.append(0)
            else:
                reached.append(1 if np.random.random() < rate else 0)

    return reached

funnel_results = df.apply(simulate_funnel, axis=1)

for i, step_name in enumerate(STEPS):
    col = f'reached_{step_name.split(":")[0].strip().lower().replace(" ", "_")}'
    df[col] = [r[i] for r in funnel_results]

# Time spent per step
df['time_step1_min'] = np.clip(np.random.lognormal(1.5, 0.8, N), 0.5, 30).round(1)
df['time_step2_min'] = np.where(df['reached_step_2'] == 1,
                                 np.clip(np.random.lognormal(1.2, 0.6, N), 0.3, 15).round(1), 0)
df['time_step3_min'] = np.where(df['reached_step_3'] == 1,
                                 np.clip(np.random.lognormal(2.0, 0.7, N), 1, 25).round(1), 0)
df['time_step4_min'] = np.where(df['reached_step_4'] == 1,
                                 np.clip(np.random.lognormal(2.3, 0.9, N), 1, 40).round(1), 0)
df['time_step5_min'] = np.where(df['reached_step_5'] == 1,
                                 np.clip(np.random.lognormal(1.0, 0.5, N), 0.5, 10).round(1), 0)

# dropout reasons
dropout_reasons = [
    'Form too long', 'KYC document rejected', 'Technical error',
    'Session timeout', 'Changed mind', 'Competitor offer',
    'Verification delay', 'Missing document', 'Unknown'
]
dropout_weights = [0.22, 0.16, 0.08, 0.06, 0.12, 0.10, 0.08, 0.07, 0.11]  # Signicat: 26% complexity, 23% ID issues

df['completed_onboarding'] = df['reached_step_6']

#figure out last step each person reached
def get_last_step(row):
    for i in range(5, -1, -1):
        col = f'reached_step_{i+1}'
        if row[col] == 1:
            return STEPS[i]
    return STEPS[0]

df['last_step_reached'] = df.apply(get_last_step, axis=1)

# assign dropout reason for people who didnt finish
non_completers = df[df['completed_onboarding'] == 0].index
df.loc[non_completers, 'dropout_reason'] = np.random.choice(
    dropout_reasons, len(non_completers), p=dropout_weights
)
df['dropout_reason'] = df['dropout_reason'].fillna('Completed')

# acquisition cost
df['acquisition_cost_eur'] = df['acquisition_channel'].map(
    {ch: p['cac'] for ch, p in channel_profiles.items()}
)
df['acquisition_cost_eur'] = (df['acquisition_cost_eur'] * np.random.normal(1, 0.15, N)).clip(5, 200).round(2)

# post onboarding metrics (only for completers)
completers_mask = df['completed_onboarding'] == 1
n_completers = completers_mask.sum()

df.loc[completers_mask, 'transactions_90d'] = np.clip(
    np.random.poisson(15, n_completers), 0, 100
)
df.loc[completers_mask, 'avg_balance_90d_eur'] = np.clip(
    np.random.lognormal(7, 1.2, n_completers), 100, 50000
).round(2)
df.loc[completers_mask, 'product_upsell_90d'] = np.random.choice(
    [0, 1], n_completers, p=[0.88, 0.12]  # industry: 8-15% cross-sell in 90 days
)
df.loc[completers_mask, 'nps_score'] = np.clip(
    np.random.normal(7.5, 2, n_completers), 0, 10
).round(0).astype(int)

df['transactions_90d'] = df['transactions_90d'].fillna(0).astype(int)
df['avg_balance_90d_eur'] = df['avg_balance_90d_eur'].fillna(0)
df['product_upsell_90d'] = df['product_upsell_90d'].fillna(0).astype(int)
df['nps_score'] = df['nps_score'].fillna(0).astype(int)

# save it
os.makedirs('../data', exist_ok=True)
df.to_csv('../data/onboarding_funnel.csv', index=False)

print(f"Records generated: {len(df)}")
print(f"Overall conversion rate: {df['completed_onboarding'].mean():.1%}")
print(f"Completers: {completers_mask.sum()}")
print(f"\nConversion by channel:")
for ch in channels:
    rate = df[df['acquisition_channel'] == ch]['completed_onboarding'].mean()
    count = (df['acquisition_channel'] == ch).sum()
    print(f"  {ch:20s}: {rate:.1%} (n={count})")
print(f"\nColumns: {list(df.columns)}")
