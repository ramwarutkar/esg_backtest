from scipy import stats
from metrics import analyze_fund_pair

ESG_FUNDS = {
    "SBI ESG Exclusionary Strategy Fund": 119709,
    "ICICI Prudential ESG Exclusionary Strategy Fund": 148517,
    "Axis ESG Integration Strategy Fund": 147928,
}

BENCHMARK_CODE = 120716


def run_anova_on_excess_returns(esg_funds, benchmark_code, years=5):
    """
    One-way ANOVA: tests whether the DAILY EXCESS RETURN (ESG return minus
    benchmark return, same days) differs significantly across the different
    ESG fund providers. A significant result means fund-to-fund variation
    is itself meaningful, not just noise.
    """
    excess_return_groups = []
    fund_names = []

    for fund_name, esg_code in esg_funds.items():
        try:
            result = analyze_fund_pair(esg_scheme_code=esg_code, benchmark_scheme_code=benchmark_code, years=years)
        except RuntimeError as e:
            print(f"SKIPPED {fund_name}: {e}")
            continue

        merged = result['merged_data']
        excess_return = merged['esg_return'] - merged['bench_return']
        excess_return_groups.append(excess_return.values)
        fund_names.append(fund_name)

    f_stat, p_value = stats.f_oneway(*excess_return_groups)

    group_means = {name: group.mean() for name, group in zip(fund_names, excess_return_groups)}

    return {
        "fund_names": fund_names,
        "f_statistic": f_stat,
        "p_value": p_value,
        "significant_at_5pct": p_value < 0.05,
        "group_mean_excess_returns": group_means
    }


if __name__ == "__main__":
    result = run_anova_on_excess_returns(ESG_FUNDS, BENCHMARK_CODE)

    print(f"\nFunds compared: {', '.join(result['fund_names'])}\n")

    print("--- Mean Daily Excess Return by Fund ---")
    for name, mean_val in result['group_mean_excess_returns'].items():
        print(f"  {name}: {mean_val:+.6f}")

    print(f"\n--- One-Way ANOVA ---")
    print(f"  F-statistic: {result['f_statistic']:.4f}")
    print(f"  p-value: {result['p_value']:.4f}")
    print(f"  Significant at 5%? {result['significant_at_5pct']}")

    print(f"\n--- Interpretation ---")
    if result['significant_at_5pct']:
        print("Fund-to-fund variation in excess return is statistically significant.")
        print("This means WHICH ESG fund you pick matters more than whether it's 'ESG' at all —")
        print("there is no consistent, uniform 'ESG effect' across providers in this sample.")
    else:
        print("No statistically significant difference in excess return across the three funds.")
        print("Despite the funds pointing in different directions (some ESG-positive, one ESG-negative),")
        print("this spread is not large enough, relative to daily volatility, to rule out chance —")
        print("a larger sample of funds or a longer time window would be needed to say more.")