from scipy import stats
from metrics import analyze_fund_pair


def run_paired_ttest(esg_returns, bench_returns):
    """
    Paired t-test on daily returns: tests whether the average daily
    return DIFFERENCE between the ESG fund and benchmark is distinguishable
    from zero (i.e. from pure chance).
    """
    differences = esg_returns - bench_returns

    t_stat, p_value = stats.ttest_rel(esg_returns, bench_returns)

    return {
        "mean_daily_diff": differences.mean(),
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant_at_5pct": p_value < 0.05,
        "n_days": len(differences)
    }


def check_distribution_shape(returns_diff):
    """
    Basic normality/shape diagnostics — checked before trusting a
    parametric test like the paired t-test.
    """
    skewness = stats.skew(returns_diff)
    kurtosis = stats.kurtosis(returns_diff)

    sample_size = min(5000, len(returns_diff))
    shapiro_stat, shapiro_p = stats.shapiro(returns_diff.sample(sample_size, random_state=42))

    return {
        "skewness": skewness,
        "kurtosis": kurtosis,
        "shapiro_p_value": shapiro_p,
        "looks_reasonably_normal": abs(skewness) < 1 and abs(kurtosis) < 3
    }


if __name__ == "__main__":
    result = analyze_fund_pair(esg_scheme_code=119709, benchmark_scheme_code=120716, years=5)
    merged = result['merged_data']

    print(f"ESG Fund: {result['esg_name']}")
    print(f"Benchmark: {result['bench_name']}")
    print(f"Sample size: {result['n_days']} trading days\n")

    diff = merged['esg_return'] - merged['bench_return']

    print("--- Distribution Shape Check ---")
    shape = check_distribution_shape(diff)
    for k, v in shape.items():
        print(f"  {k}: {v}")

    print("\n--- Paired T-Test ---")
    ttest = run_paired_ttest(merged['esg_return'], merged['bench_return'])
    for k, v in ttest.items():
        print(f"  {k}: {v}")

    print("\n--- Interpretation ---")
    if ttest['significant_at_5pct']:
        direction = "outperformed" if ttest['mean_daily_diff'] > 0 else "underperformed"
        print(f"The ESG fund {direction} the benchmark by a statistically significant margin (p = {ttest['p_value']:.4f}).")
    else:
        print(f"No statistically significant difference detected (p = {ttest['p_value']:.4f}) — the observed gap could plausibly be due to chance.")