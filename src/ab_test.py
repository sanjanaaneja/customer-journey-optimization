# A/B test for simplified KYC form

import hashlib
import os
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

import sys
sys.path.insert(0, '..')
from style_config import *

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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


def _assign_group(prospect_id):
    """assign control or test using hash"""
    digest = hashlib.md5(prospect_id.encode('utf-8')).hexdigest()
    last_hex = int(digest[-1], 16)
    return 'control' if last_hex % 2 == 0 else 'test'


def _apply_test_lift(df, lift=0.08):
    """Apply conversion lift to test group at step 4"""
    df = df.copy()

    # get transition rates so we can propagate new conversions forward
    step4_total = df['reached_step_4'].sum()
    step5_given_4 = df['reached_step_5'].sum() / step4_total if step4_total > 0 else 0.0
    step6_given_5 = df['reached_step_6'].sum() / df['reached_step_5'].sum() if df['reached_step_5'].sum() > 0 else 0.0

    # find test group people who got stuck at step 3
    eligible_mask = (
        (df['group'] == 'test') &
        (df['reached_step_3'] == 1) &
        (df['reached_step_4'] == 0)
    )
    eligible_indices = df.loc[eligible_mask].index

    test_step3 = df.loc[(df['group'] == 'test') & (df['reached_step_3'] == 1)]
    current_rate = test_step3['reached_step_4'].mean()
    target_rate = current_rate * (1 + lift)

    if current_rate < 1.0:
        flip_prob = (target_rate - current_rate) / (1.0 - current_rate)
    else:
        flip_prob = 0.0
    flip_prob = min(max(flip_prob, 0.0), 1.0)

    np.random.seed(42)
    flips = np.random.binomial(1, flip_prob, size=len(eligible_indices))
    flipped = eligible_indices[flips == 1]

    # flip step 4
    df.loc[flipped, 'reached_step_4'] = 1

    # propagate to step 5
    s5_flips = np.random.binomial(1, step5_given_4, size=len(flipped))
    s5_reached = flipped[s5_flips == 1]
    df.loc[s5_reached, 'reached_step_5'] = 1

    #propagate to step 6
    s6_flips = np.random.binomial(1, step6_given_5, size=len(s5_reached))
    s6_reached = s5_reached[s6_flips == 1]
    df.loc[s6_reached, 'reached_step_6'] = 1

    return df


def run_ab_test(data_path='../data/onboarding_funnel.csv', output_dir='../outputs/figures/'):
    """Run the AB test and return results."""
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} prospects from {data_path}")

    # assign groups
    df['group'] = df['prospect_id'].apply(_assign_group)
    n_control = (df['group'] == 'control').sum()
    n_test = (df['group'] == 'test').sum()
    print(f"\nGroup assignment: Control = {n_control} | Test = {n_test}")

    # apply the test lift
    df = _apply_test_lift(df, lift=0.08)

    # calculate step 4 conversion (among people who reached step 3)
    control = df.loc[(df['group'] == 'control') & (df['reached_step_3'] == 1)]
    test = df.loc[(df['group'] == 'test') & (df['reached_step_3'] == 1)]

    control_rate = control['reached_step_4'].mean()
    test_rate = test['reached_step_4'].mean()
    relative_lift = (test_rate - control_rate) / control_rate if control_rate > 0 else 0.0

    print("\n" + "=" * 60)
    print("A/B TEST: Simplified KYC Form vs Current Form")
    print("=" * 60)
    print(f"\nMetric: Step 4 conversion rate (among those who completed Step 3)")
    # H0: no difference, H1: there is a difference

    alpha = 0.05

    # two proportion z-test
    count = np.array([test['reached_step_4'].sum(), control['reached_step_4'].sum()])
    nobs = np.array([len(test), len(control)])

    z_stat, p_value = proportions_ztest(count, nobs, alternative='two-sided')

    # confidence interval for the difference
    diff = test_rate - control_rate
    se_diff = np.sqrt(
        test_rate * (1 - test_rate) / len(test)
        + control_rate * (1 - control_rate) / len(control)
    )
    ci_lower = diff - 1.96 * se_diff
    ci_upper = diff + 1.96 * se_diff

    significant = p_value < alpha

    print(f"\nControl conversion rate: {control_rate:.4f} ({control_rate * 100:.2f}%)")
    print(f"Test conversion rate:    {test_rate:.4f} ({test_rate * 100:.2f}%)")
    print(f"Absolute difference:     {diff:+.4f} ({diff * 100:+.2f} pp)")
    print(f"Relative lift:           {relative_lift:+.2%}")
    print(f"Z-statistic:             {z_stat:.4f}")
    print(f"P-value:                 {p_value:.6f}")
    print(f"95% CI for difference:   [{ci_lower:+.4f}, {ci_upper:+.4f}]")
    print(f"Significant at 5%:       {'YES' if significant else 'NO'}")

    # recommendation
    print("\nRECOMMENDATION:")
    if significant and diff > 0:
        print(f"  The simplified form shows a significant improvement of {relative_lift:+.1%}")
        print(f"  in Step 4 conversion (p={p_value:.4f}).")
        print("  -> Roll out the simplified form to all users.")
    elif significant and diff < 0:
        print("  The simplified form made things worse. Do NOT roll out.")
    else:
        print(f"  No significant difference found (p={p_value:.4f}).")
        print("  -> Continue the experiment or try a bigger change.")
    print()

    # Figure 1 - bar chart comparing control vs test
    fig, ax = plt.subplots(figsize=(7, 5))

    labels = ['Control\n(Current Form)', 'Test\n(Simplified Form)']
    rates = [control_rate * 100, test_rate * 100]
    colors = [PRIMARY, ACCENT]

    bars = ax.bar(labels, rates, color=colors, width=0.5, edgecolor='white')

    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=13)

    ax.set_ylabel('Step 4 Conversion Rate (%)')
    ax.set_title('A/B Test: KYC Form Step 4 Conversion')
    ax.set_ylim(0, max(rates) * 1.25)

    # p-value annotation
    sig_text = f'p = {p_value:.4f}  ({"Significant" if significant else "Not significant"})'
    ax.annotate(sig_text, xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', va='top', fontsize=10, color=MUTED,
                bbox=dict(boxstyle='round,pad=0.3', facecolor=LIGHT, edgecolor=MUTED, alpha=0.8))

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '11_ab_test_conversion.png'))
    plt.close(fig)
    print(f"  Saved: {os.path.join(output_dir, '11_ab_test_conversion.png')}")

    # Figure 2 - confidence interval
    fig, ax = plt.subplots(figsize=(8, 4))

    # CI line
    ax.plot([ci_lower * 100, ci_upper * 100], [0, 0], color=ACCENT, linewidth=3)
    ax.plot(ci_lower * 100, 0, '|', color=ACCENT, markersize=20, markeredgewidth=3)
    ax.plot(ci_upper * 100, 0, '|', color=ACCENT, markersize=20, markeredgewidth=3)
    # point estimate
    ax.plot(diff * 100, 0, 'o', color=ACCENT, markersize=12, zorder=5)
    ax.annotate(f'{diff * 100:+.2f} pp', xy=(diff * 100, 0), xytext=(diff * 100, 0.15),
                ha='center', fontsize=12, fontweight='bold', color=TEXT,
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8))

    # no effect line
    ax.axvline(0, color=DANGER, linewidth=2, linestyle='--', label='No effect')
    ax.text(0.02, 0.30, 'No effect', color=DANGER, fontsize=10, fontweight='bold')

    # CI bounds labels
    ax.text(ci_lower * 100, -0.18, f'{ci_lower * 100:+.2f} pp', ha='center', fontsize=9, color=MUTED)
    ax.text(ci_upper * 100, -0.18, f'{ci_upper * 100:+.2f} pp', ha='center', fontsize=9, color=MUTED)

    ax.set_title('95% Confidence Interval for Conversion Rate Difference')
    ax.set_xlabel('Difference in Step 4 Conversion (percentage points)')
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '12_ab_test_confidence_interval.png'))
    plt.close(fig)
    print(f"  Saved: {os.path.join(output_dir, '12_ab_test_confidence_interval.png')}")
    print()

    results = {
        'control_rate': round(control_rate, 6),
        'test_rate': round(test_rate, 6),
        'lift': round(relative_lift, 6),
        'p_value': round(p_value, 6),
        'ci_lower': round(ci_lower, 6),
        'ci_upper': round(ci_upper, 6),
        'significant': significant,
    }
    return results


if __name__ == '__main__':
    results = run_ab_test()
    print("Results dict:")
    for k, v in results.items():
        print(f"  {k}: {v}")
