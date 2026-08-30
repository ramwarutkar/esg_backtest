from metrics import analyze_fund_pair
from statistical_tests import run_paired_ttest
from anova_test import run_anova_on_excess_returns
from analyst_agent import generate_analyst_summary, generate_single_fund_summary

ESG_FUNDS = {
    "SBI ESG Exclusionary Strategy Fund": 119709,
    "ICICI Prudential ESG Exclusionary Strategy Fund": 148517,
    "Axis ESG Integration Strategy Fund": 147928,
    "Quantum ESG Best In Class Strategy Fund": 147371,
}

BENCHMARK_CODE = 120716
BENCHMARK_NAME = "UTI Nifty 50 Index Fund"


def run_full_pipeline(esg_funds, benchmark_code, years=5):
    """
    The complete, live pipeline:
    1. Fetch + compute metrics + t-test for each ESG fund vs benchmark
    2. Run ANOVA across all funds' excess returns (skipped if fewer than 2 funds)
    3. Feed the REAL results into the Analyst Agent for narration
    Returns a NAV series (rebased to 100) per fund for charting too.
    """
    fund_results = []

    for fund_name, esg_code in esg_funds.items():
        print(f"Analyzing {fund_name}...")
        try:
            result = analyze_fund_pair(esg_scheme_code=esg_code, benchmark_scheme_code=benchmark_code, years=years)
        except RuntimeError as e:
            print(f"  SKIPPED — {e}")
            continue

        merged = result['merged_data']
        ttest = run_paired_ttest(merged['esg_return'], merged['bench_return'])

        # Build a rebased-to-100 NAV series for charting, from the same
        # aligned returns already computed — no extra fetching needed.
        esg_nav_rebased = 100 * (1 + merged['esg_return']).cumprod()
        bench_nav_rebased = 100 * (1 + merged['bench_return']).cumprod()
        nav_series = {
            "dates": merged['date'].dt.strftime("%Y-%m-%d").tolist(),
            "esg_nav": esg_nav_rebased.tolist(),
            "bench_nav": bench_nav_rebased.tolist()
        }

        fund_entry = {
            "fund_name": fund_name,
            "sharpe_esg": result['esg_metrics']['sharpe'],
            "sharpe_bench": result['bench_metrics']['sharpe'],
            "cagr_esg": result['esg_metrics']['cagr'],
            "cagr_bench": result['bench_metrics']['cagr'],
            "volatility_esg": result['esg_metrics']['volatility'],
            "max_drawdown_esg": result['esg_metrics']['max_drawdown'],
            "sharpe_diff": result['esg_metrics']['sharpe'] - result['bench_metrics']['sharpe'],
            "p_value": ttest['p_value'],
            "significant": ttest['significant_at_5pct'],
            "nav_series": nav_series
        }
        print(f"  Generating narration for {fund_name}...")
        fund_entry["fund_summary"] = generate_single_fund_summary(fund_entry)
        fund_results.append(fund_entry)

    if len(fund_results) == 0:
        raise RuntimeError("Could not fetch data for any of the selected funds.")

    anova_result = None
    if len(fund_results) >= 2:
        anova_result = run_anova_on_excess_returns(
            {r["fund_name"]: esg_funds[r["fund_name"]] for r in fund_results},
            benchmark_code, years
        )

    # Only worth an LLM call if there's actually a cross-fund comparison to narrate
    summary = None
    if anova_result is not None:
        print("\nGenerating overall cross-fund summary...")
        summary = generate_analyst_summary(fund_results, anova_result)

    return {
        "fund_results": fund_results,
        "anova_result": anova_result,
        "analyst_summary": summary
    }


if __name__ == "__main__":
    output = run_full_pipeline(ESG_FUNDS, BENCHMARK_CODE)

    print("\n" + "=" * 70)
    print("  PER-FUND RESULTS (LIVE DATA)")
    print("=" * 70)
    for r in output['fund_results']:
        sig_flag = "SIGNIFICANT" if r['significant'] else "not significant"
        print(f"  {r['fund_name']:<50} Sharpe diff: {r['sharpe_diff']:+.4f}  (p={r['p_value']:.4f}, {sig_flag})")

    if output['anova_result']:
        print("\n" + "=" * 70)
        print("  ANOVA (LIVE DATA)")
        print("=" * 70)
        print(f"  F = {output['anova_result']['f_statistic']:.4f}, p = {output['anova_result']['p_value']:.4f}")

    print("\n" + "=" * 70)
    print("  ANALYST AGENT SUMMARY")
    print("=" * 70)
    print(output['analyst_summary'])