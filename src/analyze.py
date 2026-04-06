# Customer journey analysis - digital onboarding funnel

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import warnings
warnings.filterwarnings('ignore')

# chart styling
import sys, os
sys.path.insert(0, '..')
from style_config import *

plt.rcParams.update({
    'figure.facecolor': '#FFFFFF',
    'axes.facecolor': '#FFFFFF',
    'axes.edgecolor': LIGHT,
    'text.color': TEXT,
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
})


def run_sql(filepath, conn):
    with open(filepath) as f:
        return pd.read_sql(f.read(), conn)


# load data
print("=" * 60)
print("CUSTOMER JOURNEY OPTIMIZATION - DIGITAL ONBOARDING")
print("=" * 60)

df = pd.read_csv('../data/onboarding_funnel.csv', parse_dates=['start_date'])

# load into sqlite for SQL-driven EDA
conn = sqlite3.connect(':memory:')
df.to_sql('onboarding_funnel', conn, index=False)

print("\nDataset: %d prospects" % len(df))
print("Conversion rate: %.1f%%" % (df['completed_onboarding'].mean() * 100))
print("Period: %s to %s" % (df['start_date'].min().date(), df['start_date'].max().date()))

step_cols = ['reached_step_1', 'reached_step_2', 'reached_step_3',
             'reached_step_4', 'reached_step_5', 'reached_step_6']
step_labels = ['Landing\nPage', 'Account\nSelection', 'Personal\nDetails',
               'KYC\nUpload', 'Identity\nVerification', 'First\nTransaction']

# --- Exploratory Analysis (SQL) ---

# Figure 1 - conversion funnel (SQL: 01_funnel_overview)
print("\nFUNNEL ANALYSIS")

funnel_sql = run_sql('../sql/01_funnel_overview.sql', conn)

fig, ax = plt.subplots(figsize=(11, 6))

funnel_counts = [int(funnel_sql['step_%d' % i].iloc[0]) for i in range(1, 7)]
total = int(funnel_sql['total_prospects'].iloc[0])
funnel_rates = [c / total * 100 for c in funnel_counts]
step_drop = [0] + [(funnel_counts[i] - funnel_counts[i+1]) / funnel_counts[i] * 100
                    for i in range(len(funnel_counts) - 1)]

colors_funnel = [ACCENT] + [SECONDARY] * 4 + [SUCCESS]
bars = ax.bar(range(len(step_labels)), funnel_counts, color=colors_funnel,
              edgecolor='white', width=0.6)

for i, (count, rate) in enumerate(zip(funnel_counts, funnel_rates)):
    ax.text(i, count + 80, '%d' % count, ha='center', fontsize=11, fontweight='bold', color=TEXT)
    ax.text(i, count + 350, '%.0f%%' % rate, ha='center', fontsize=9, color=MUTED)
    if i > 0:
        drop = step_drop[i]
        ax.annotate('v %.0f%% drop' % drop,
                     xy=(i - 0.5, (funnel_counts[i-1] + funnel_counts[i]) / 2),
                     fontsize=8, color=DANGER, ha='center', fontstyle='italic')

ax.set_xticks(range(len(step_labels)))
ax.set_xticklabels(step_labels, fontsize=10)
ax.set_ylabel('Number of Prospects')
ax.set_title('Digital Onboarding Conversion Funnel', fontsize=15, fontweight='bold')
ax.set_ylim(0, max(funnel_counts) * 1.15)

conversion_pct = float(funnel_sql['conversion_rate_pct'].iloc[0])
ax.text(5, funnel_counts[-1] * 0.5,
        'End-to-end\nconversion: %.1f%%' % conversion_pct,
        ha='center', fontsize=11, fontweight='bold', color=SUCCESS,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#E8F8F0', edgecolor=SUCCESS, alpha=0.8))

plt.tight_layout()
plt.savefig('../outputs/figures/01_conversion_funnel.png')
plt.close()
print("OK Saved: 01_conversion_funnel.png")

# Figure 2 - funnel by channel (pandas - extends SQL channel analysis with per-step breakdown)
fig, ax = plt.subplots(figsize=(12, 6))

channel_order = df.groupby('acquisition_channel')['completed_onboarding'].mean().sort_values(ascending=False).index

x = np.arange(len(step_labels))
width = 0.12
colors_ch = [ACCENT, SECONDARY, TERTIARY, PURPLE, TEAL, MUTED]

for j, ch in enumerate(channel_order):
    ch_data = df[df['acquisition_channel'] == ch]
    rates = [ch_data[col].mean() * 100 for col in step_cols]
    ax.bar(x + j * width - (len(channel_order) * width / 2), rates,
           width, label=ch, color=colors_ch[j % len(colors_ch)], edgecolor='white')

ax.set_xticks(x)
ax.set_xticklabels(step_labels, fontsize=9)
ax.set_ylabel('Conversion Rate (%)')
ax.set_title('Funnel Conversion by Acquisition Channel', fontweight='bold', fontsize=14)
ax.legend(fontsize=8, ncol=3, loc='upper right')
ax.set_ylim(0, 105)

plt.tight_layout()
plt.savefig('../outputs/figures/02_funnel_by_channel.png')
plt.close()
print("OK Saved: 02_funnel_by_channel.png")

# Figure 3 - dropout analysis
# Left panel: where (pandas - needs last_step_reached which SQL 03 doesn't cover)
# Right panel: why (SQL: 03_dropout_reasons)
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

dropout_step = df[df['completed_onboarding'] == 0]['last_step_reached'].value_counts()
step_order_map = {s: i for i, s in enumerate([
    'Step 1: Landing Page Visit', 'Step 2: Account Type Selection',
    'Step 3: Personal Details Form', 'Step 4: KYC Document Upload',
    'Step 5: Identity Verification', 'Step 6: First Transaction'
])}
dropout_step = dropout_step.reindex(
    sorted(dropout_step.index, key=lambda x: step_order_map.get(x, 99))
)
short_labels = [s.split(': ')[1] if ': ' in s else s for s in dropout_step.index]

colors_drop = [ACCENT if 'KYC' in s or 'Personal' in s else SECONDARY for s in dropout_step.index]
axes[0].barh(short_labels, dropout_step.values, color=colors_drop, height=0.55, edgecolor='white')
for i, v in enumerate(dropout_step.values):
    axes[0].text(v + 15, i, '%d' % v, va='center', fontsize=9)
axes[0].set_xlabel('Dropouts')
axes[0].set_title('Where Prospects Drop Off', fontweight='bold')

# right panel from SQL
reasons_sql = run_sql('../sql/03_dropout_reasons.sql', conn)
reasons_sql = reasons_sql.sort_values('dropout_count', ascending=True)
axes[1].barh(reasons_sql['dropout_reason'], reasons_sql['dropout_count'],
             color=ACCENT, height=0.55, edgecolor='white')
for i, v in enumerate(reasons_sql['dropout_count']):
    axes[1].text(v + 10, i, '%d' % v, va='center', fontsize=9)
axes[1].set_xlabel('Count')
axes[1].set_title('Dropout Reasons', fontweight='bold')

plt.suptitle('Drop-off Analysis', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('../outputs/figures/03_dropout_analysis.png')
plt.close()
print("OK Saved: 03_dropout_analysis.png")

# --- Extended Analysis (Python) ---

# Figure 4 - device x age heatmap (Python - needs pivot table)
fig, ax = plt.subplots(figsize=(9, 5))

pivot = df.pivot_table(values='completed_onboarding', index='age_group',
                       columns='device', aggfunc='mean') * 100
age_order = ['18-24', '25-34', '35-44', '45-54', '55+']
pivot = pivot.reindex(age_order)

sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax,
            linewidths=1, linecolor='white',
            cbar_kws={'label': 'Conversion Rate (%)'})
ax.set_title('Conversion Rate: Age Group x Device', fontweight='bold', fontsize=14)
ax.set_ylabel('')

plt.tight_layout()
plt.savefig('../outputs/figures/04_device_age_matrix.png')
plt.close()
print("OK Saved: 04_device_age_matrix.png")

# Figure 5 - time per step (Python - SQL can't easily compute conditional means for completers vs dropouts)
fig, ax = plt.subplots(figsize=(10, 5))

time_cols = ['time_step1_min', 'time_step2_min', 'time_step3_min', 'time_step4_min', 'time_step5_min']
time_labels = ['Landing Page', 'Account Selection', 'Personal Details', 'KYC Upload', 'Verification']

completers = df[df['completed_onboarding'] == 1]
dropouts = df[df['completed_onboarding'] == 0]

x = np.arange(len(time_labels))
width = 0.35

comp_times = []
drop_times = []
for col in time_cols:
    comp_mean = completers[completers[col] > 0][col].mean()
    drop_mean = dropouts[dropouts[col] > 0][col].mean()
    comp_times.append(comp_mean if not np.isnan(comp_mean) else 0)
    drop_times.append(drop_mean if not np.isnan(drop_mean) else 0)

bars1 = ax.bar(x - width/2, comp_times, width, label='Completers', color=SUCCESS, edgecolor='white')
bars2 = ax.bar(x + width/2, drop_times, width, label='Dropouts', color=DANGER, edgecolor='white')

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, '%.1fm' % h,
                    ha='center', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(time_labels, fontsize=10)
ax.set_ylabel('Average Time (minutes)')
ax.set_title('Time Spent per Step: Completers vs. Dropouts', fontweight='bold', fontsize=14)
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig('../outputs/figures/05_time_per_step.png')
plt.close()
print("OK Saved: 05_time_per_step.png")

# --- Marketing & ROI (SQL + charts) ---
print("\nMARKETING & ROI ANALYSIS")

# Figure 6 - channel ROI (SQL: 05_channel_cost + 02_conversion_by_channel)
cost_sql = run_sql('../sql/05_channel_cost.sql', conn)
conv_sql = run_sql('../sql/02_conversion_by_channel.sql', conn)

# merge SQL results for a combined channel_metrics frame
channel_metrics = cost_sql.merge(
    conv_sql[['acquisition_channel', 'conversion_rate_pct']],
    on='acquisition_channel'
)
channel_metrics['conversion_rate'] = channel_metrics['conversion_rate_pct'] / 100.0
channel_metrics = channel_metrics.set_index('acquisition_channel')
channel_metrics = channel_metrics.sort_values('conversion_rate', ascending=False)

print("\nChannel Performance:")
print(channel_metrics[['total_prospects', 'completions', 'conversion_rate', 'avg_cost_eur', 'cost_per_conversion']])

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# conversion rate by channel
bars = axes[0].barh(channel_metrics.index, channel_metrics['conversion_rate'] * 100,
                     color=PALETTE[:len(channel_metrics)], height=0.55, edgecolor='white')
for i, (idx, row) in enumerate(channel_metrics.iterrows()):
    axes[0].text(row['conversion_rate'] * 100 + 0.5, i,
                 '%.1f%% (%d conv)' % (row['conversion_rate'] * 100, row['completions']),
                 va='center', fontsize=9)
axes[0].set_xlabel('Conversion Rate (%)')
axes[0].set_title('Conversion Rate by Channel', fontweight='bold')

# cost per conversion
cpc = channel_metrics.sort_values('cost_per_conversion', ascending=True)
colors_cpc = [SUCCESS if c < 200 else ACCENT if c < 500 else DANGER
              for c in cpc['cost_per_conversion']]
axes[1].barh(cpc.index, cpc['cost_per_conversion'], color=colors_cpc, height=0.55, edgecolor='white')
for i, v in enumerate(cpc['cost_per_conversion']):
    axes[1].text(v + 5, i, 'EUR %.0f' % v, va='center', fontsize=9, fontweight='bold')
axes[1].set_xlabel('Cost per Conversion (EUR)')
axes[1].set_title('Customer Acquisition Efficiency', fontweight='bold')

plt.suptitle('Marketing Channel Performance', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('../outputs/figures/06_channel_roi.png')
plt.close()
print("OK Saved: 06_channel_roi.png")

# Figure 7 - channel efficiency scatter (reuses SQL results from Figure 6)
fig, ax = plt.subplots(figsize=(9, 6))

for i, (ch, row) in enumerate(channel_metrics.iterrows()):
    ax.scatter(row['conversion_rate'] * 100, row['cost_per_conversion'],
               s=row['total_prospects'] / 5, color=PALETTE[i % len(PALETTE)],
               alpha=0.8, edgecolors='white', linewidth=1.5)
    ax.annotate(ch, (row['conversion_rate'] * 100, row['cost_per_conversion']),
                textcoords='offset points', xytext=(8, 8), fontsize=9)

ax.set_xlabel('Conversion Rate (%)')
ax.set_ylabel('Cost per Conversion (EUR)')
ax.set_title('Channel Efficiency Matrix', fontweight='bold', fontsize=14)

ax.axvline(channel_metrics['conversion_rate'].mean() * 100, color=MUTED, linestyle='--', alpha=0.5)
ax.axhline(channel_metrics['cost_per_conversion'].mean(), color=MUTED, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('../outputs/figures/07_channel_efficiency.png')
plt.close()
print("OK Saved: 07_channel_efficiency.png")

# --- Post-Onboarding Analysis (SQL + charts) ---
print("\nPOST-ONBOARDING VALUE ANALYSIS")

# Figure 8 - customer quality by channel (SQL: 06_post_onboarding)
post_sql = run_sql('../sql/06_post_onboarding.sql', conn)
post_sql = post_sql.set_index('acquisition_channel')

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# transactions
ch_txn = post_sql['avg_transactions_90d'].sort_values(ascending=True)
axes[0].barh(ch_txn.index, ch_txn.values, color=ACCENT, height=0.55, edgecolor='white')
for i, v in enumerate(ch_txn):
    axes[0].text(v + 0.2, i, '%.1f' % v, va='center', fontsize=9)
axes[0].set_xlabel('Avg Transactions (90 days)')
axes[0].set_title('Customer Engagement', fontweight='bold')

# balance
ch_bal = post_sql['avg_balance_eur'].sort_values(ascending=True)
axes[1].barh(ch_bal.index, ch_bal.values / 1000, color=SECONDARY, height=0.55, edgecolor='white')
for i, v in enumerate(ch_bal / 1000):
    axes[1].text(v + 0.05, i, 'EUR %.1fK' % v, va='center', fontsize=9)
axes[1].set_xlabel('Avg Balance (EUR thousands)')
axes[1].set_title('Customer Value', fontweight='bold')

# nps scores
ch_nps = post_sql['avg_nps'].sort_values(ascending=True)
colors_nps = [SUCCESS if n >= 8 else ACCENT if n >= 6 else DANGER for n in ch_nps]
axes[2].barh(ch_nps.index, ch_nps.values, color=colors_nps, height=0.55, edgecolor='white')
for i, v in enumerate(ch_nps):
    axes[2].text(v + 0.05, i, '%.1f' % v, va='center', fontsize=9)
axes[2].set_xlabel('Average NPS Score')
axes[2].set_title('Customer Satisfaction', fontweight='bold')

plt.suptitle('Post-Onboarding Customer Quality by Channel', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('../outputs/figures/08_customer_quality.png')
plt.close()
print("OK Saved: 08_customer_quality.png")

# --- Extended Analysis (Python) ---

# Figure 9 - monthly trends (Python - needs time series operations)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

df['month'] = df['start_date'].dt.to_period('M')
monthly = df.groupby('month').agg(
    prospects=('prospect_id', 'count'),
    conversions=('completed_onboarding', 'sum'),
    conversion_rate=('completed_onboarding', 'mean'),
    avg_cac=('acquisition_cost_eur', 'mean')
)
monthly.index = monthly.index.to_timestamp()

ax2 = axes[0].twinx()
axes[0].bar(monthly.index, monthly['prospects'], width=25, color=SECONDARY, alpha=0.4, label='Prospects')
axes[0].bar(monthly.index, monthly['conversions'], width=25, color=SUCCESS, alpha=0.7, label='Conversions')
ax2.plot(monthly.index, monthly['conversion_rate'] * 100, color=ACCENT, linewidth=2.5, marker='o', markersize=4, label='Conv. Rate')
axes[0].set_ylabel('Count')
ax2.set_ylabel('Conversion Rate (%)')
axes[0].set_title('Monthly Onboarding Volume & Conversion', fontweight='bold')
lines1, labels1 = axes[0].get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
axes[0].legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc='upper left')

# product interest over time
product_monthly = df.groupby([df['start_date'].dt.to_period('M'), 'product_interest']).size().unstack(fill_value=0)
product_monthly.index = product_monthly.index.to_timestamp()
product_monthly.plot(kind='area', ax=axes[1], stacked=True, alpha=0.7,
                     color=[ACCENT, SECONDARY, TERTIARY, TEAL])
axes[1].set_ylabel('Prospects')
axes[1].set_title('Product Interest Over Time', fontweight='bold')
axes[1].legend(fontsize=8, loc='upper left')

plt.tight_layout()
plt.savefig('../outputs/figures/09_monthly_trends.png')
plt.close()
print("OK Saved: 09_monthly_trends.png")

# Figure 10 - KYC bottleneck
# Left panel: KYC conversion by device (SQL: 04_device_comparison)
# Right panel: KYC time distribution (Python - histogram)
device_sql = run_sql('../sql/04_device_comparison.sql', conn)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# kyc conversion by device - use SQL results
# SQL gives overall conversion and KYC rate; we also need step 4->5 progression
# recalculate step-level from SQL device data for the chart
device_sql_indexed = device_sql.set_index('device')
devices_list = device_sql_indexed.index.tolist()

x = np.arange(len(devices_list))
width = 0.35

# KYC rate from SQL is reached_step_3 / total, but we need step4/step3-reacher and step5/step3-reacher
# SQL 04 gives reached_kyc (which is step 3 count) and kyc_rate_pct
# For the detailed step 4 and 5 rates among step 3 reachers we use pandas (quick calc)
kyc_device = df[df['reached_step_3'] == 1].groupby('device').agg(
    reached_kyc=('reached_step_4', 'mean'),
    reached_verification=('reached_step_5', 'mean'),
).round(3) * 100

axes[0].bar(x - width/2, kyc_device.loc[devices_list, 'reached_kyc'], width,
            label='KYC Upload', color=ACCENT, edgecolor='white')
axes[0].bar(x + width/2, kyc_device.loc[devices_list, 'reached_verification'], width,
            label='ID Verification', color=SECONDARY, edgecolor='white')
axes[0].set_xticks(x)
axes[0].set_xticklabels(devices_list, fontsize=10)
axes[0].set_ylabel('Step Completion (%)')
axes[0].set_title('KYC Conversion by Device', fontweight='bold')
axes[0].legend(fontsize=9)
for bars_set in axes[0].containers:
    for bar in bars_set:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2, h + 0.5, '%.0f%%' % h,
                     ha='center', fontsize=8)

# KYC time distribution (Python)
kyc_times = df[df['time_step4_min'] > 0]['time_step4_min']
axes[1].hist(kyc_times, bins=30, color=ACCENT, edgecolor='white', alpha=0.8)
axes[1].axvline(kyc_times.median(), color=DANGER, linestyle='--', linewidth=2,
                label='Median: %.1f min' % kyc_times.median())
axes[1].set_xlabel('Time Spent (minutes)')
axes[1].set_ylabel('Count')
axes[1].set_title('KYC Upload Time Distribution', fontweight='bold')
axes[1].legend(fontsize=9)

plt.suptitle('KYC Bottleneck Analysis', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('../outputs/figures/10_kyc_bottleneck.png')
plt.close()
print("OK Saved: 10_kyc_bottleneck.png")

# close sqlite connection
conn.close()

# Summary
print("\nSUMMARY METRICS")

total_cost = df['acquisition_cost_eur'].sum()
total_conversions = df['completed_onboarding'].sum()
comp = df[df['completed_onboarding'] == 1]

summary = {
    'Metric': [
        'Total Prospects', 'Overall Conversion Rate', 'Total Conversions',
        'Best Channel (Conversion)', 'Worst Channel (Conversion)',
        'Avg Customer Acquisition Cost', 'Total Marketing Spend',
        'Biggest Dropout Step', 'Top Dropout Reason',
        'Avg NPS (Completers)', 'Avg 90-day Transactions (Completers)',
        'Cross-sell Rate (90d)'
    ],
    'Value': [
        '%d' % len(df),
        '%.1f%%' % (df['completed_onboarding'].mean() * 100),
        '%d' % total_conversions,
        '%s (%.1f%%)' % (channel_metrics.index[0], channel_metrics.iloc[0]['conversion_rate'] * 100),
        '%s (%.1f%%)' % (channel_metrics.index[-1], channel_metrics.iloc[-1]['conversion_rate'] * 100),
        'EUR %.0f' % df['acquisition_cost_eur'].mean(),
        'EUR %s' % format(int(total_cost), ','),
        df[df['completed_onboarding'] == 0]['last_step_reached'].value_counts().index[0],
        df[df['completed_onboarding'] == 0]['dropout_reason'].value_counts().index[0],
        '%.1f/10' % comp['nps_score'].mean(),
        '%.1f' % comp['transactions_90d'].mean(),
        '%.1f%%' % (comp['product_upsell_90d'].mean() * 100)
    ]
}
pd.DataFrame(summary).to_csv('../data/journey_summary.csv', index=False)
print("OK Saved: journey_summary.csv")
print("\nALL OUTPUTS GENERATED SUCCESSFULLY")
