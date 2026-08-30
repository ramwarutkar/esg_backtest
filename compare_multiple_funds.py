from metrics import analyze_fund_pair
from statistical_tests import run_paired_ttest, check_distribution_shape

# Scheme codes gathered earlier via mfapi.in/mf/search
ESG_FUNDS = {
    "SBI ESG Exclusionary Strategy Fund": 119709,
    "ICICI Prudential ESG Exclusionary Strategy Fund": 148517,
    "Axis ESG Integration Strategy Fund": 147928,
}

BENCHMARK_CODE = 120716  # UTI Nifty 50 Index Fund - Direct Plan - Growth
BENCHMARK_NAME = "UTI Nifty 50 Index Fund"


def run_comparison(fund_name, esg_code, benchmark_code, years=5):
    print(f"\n{'='*70}")
    print(f"  {fund_name}  vs.  {BENCHMARK_NAME}")
    print(f"{'='*70}")

    try:
        result = analyze_fund_pair(esg_scheme_code=esg_code, benchmark_scheme_code=benchmark_code, years=years)
    except RuntimeError as e:
        print(f"  SKIPPED — data fetch failed: {e}")
        return None

    merged = result['merged_data']
    diff = merged['esg_return'] - merged['bench_return']

    print(f"  Sample size: {result['n_days']} trading days")
    print(f"\n  ESG Sharpe:       {result['esg_metrics']['sharpe']:.4f}")
    print(f"  Benchmark Sharpe: {result['bench_metrics']['sharpe']:.4f}")
    print(f"  ESG CAGR:         {result['esg_metrics']['cagr']:.4f}")
    print(f"  Benchmark CAGR:   {result['bench_metrics']['cagr']:.4f}")
    print(f"  ESG Max DD:       {result['esg_metrics']['max_drawdown']:.4f}")
    print(f"  Benchmark Max DD: {result['bench_metrics']['max_drawdown']:.4f}")

    ttest = run_paired_ttest(merged['esg_return'], merged['bench_return'])
    print(f"\n  Paired t-test: t = {ttest['t_statistic']:.4f}, p = {ttest['p_value']:.4f}")
    print(f"  Significant at 5%? {ttest['significant_at_5pct']}")

    return {
        "fund_name": fund_name,
        "sharpe_esg": result['esg_metrics']['sharpe'],
        "sharpe_bench": result['bench_metrics']['sharpe'],
        "sharpe_diff": result['esg_metrics']['sharpe'] - result['bench_metrics']['sharpe'],
        "p_value": ttest['p_value'],
        "significant": ttest['significant_at_5pct']
    }


if __name__ == "__main__":
    all_results = []

    for fund_name, esg_code in ESG_FUNDS.items():
        outcome = run_comparison(fund_name, esg_code, BENCHMARK_CODE)
        if outcome:
            all_results.append(outcome)

    print(f"\n\n{'='*70}")
    print("  SUMMARY ACROSS ALL ESG FUNDS")
    print(f"{'='*70}")
    for r in all_results:
        sig_flag = "SIGNIFICANT" if r['significant'] else "not significant"
        print(f"  {r['fund_name']:<50} Sharpe diff: {r['sharpe_diff']:+.4f}  (p={r['p_value']:.4f}, {sig_flag})")