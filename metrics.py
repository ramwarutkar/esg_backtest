import requests
import pandas as pd
import numpy as np
import time


def get_nav_history(scheme_code, max_retries=3, backoff_seconds=2):
    """
    Fetch full historical NAV for a mutual fund scheme from mfapi.in.
    Retries on failure with increasing backoff.
    """
    url = f"https://api.mfapi.in/mf/{scheme_code}"

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict) or 'data' not in data or 'meta' not in data:
                raise ValueError(f"Unexpected response format for scheme {scheme_code}: {data}")

            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
            df['nav'] = df['nav'].astype(float)
            df = df.sort_values('date').reset_index(drop=True)
            return df, data['meta']

        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to fetch scheme {scheme_code} after {max_retries} attempts: {e}"
                )
            wait_time = backoff_seconds * attempt
            print(f"  Attempt {attempt} failed for scheme {scheme_code} ({e}). Retrying in {wait_time}s...")
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch scheme {scheme_code}: no valid response received.")


def compute_metrics(returns, risk_free_rate=0.06):
    """Compute CAGR, volatility, Sharpe ratio, and max drawdown from a daily returns series."""
    trading_days = 252

    cagr = (1 + returns.mean()) ** trading_days - 1
    volatility = returns.std() * np.sqrt(trading_days)

    daily_rf = risk_free_rate / trading_days
    excess_returns = returns - daily_rf
    sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(trading_days) if returns.std() > 0 else np.nan

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown
    }


# ---------- Simple in-memory NAV cache ----------
# Fetching a scheme's NAV history is the same regardless of WHY you need it
# (a t-test, ANOVA, a chart). Caching it here means each scheme is fetched
# from mfapi.in at most ONCE per server run, no matter how many different
# analyses need it.
_nav_cache = {}


def get_cached_nav(scheme_code):
    if scheme_code not in _nav_cache:
        df, meta = get_nav_history(scheme_code)
        _nav_cache[scheme_code] = (df, meta)
    return _nav_cache[scheme_code]


def get_fund_returns(scheme_code, years=5):
    """
    Fetches (from cache if available) and returns a fund's daily returns
    series restricted to the requested lookback window, plus its metadata.
    """
    df, meta = get_cached_nav(scheme_code)

    cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
    df = df[df['date'] >= cutoff].reset_index(drop=True)

    returns = df.set_index('date')['nav'].pct_change().dropna()
    return returns, meta


def analyze_fund_pair(esg_scheme_code, benchmark_scheme_code, years=5):
    """
    Fetches (or reuses cached) returns for an ESG fund and its benchmark,
    aligns them on common dates, computes daily returns, and returns
    metrics for both plus the merged returns series.
    """
    esg_returns, esg_meta = get_fund_returns(esg_scheme_code, years)
    bench_returns, bench_meta = get_fund_returns(benchmark_scheme_code, years)

    merged = pd.DataFrame({
        "esg_return": esg_returns,
        "bench_return": bench_returns
    }).dropna().reset_index()

    esg_metrics = compute_metrics(merged['esg_return'])
    bench_metrics = compute_metrics(merged['bench_return'])

    return {
        "esg_name": esg_meta['scheme_name'],
        "bench_name": bench_meta['scheme_name'],
        "merged_data": merged,
        "esg_metrics": esg_metrics,
        "bench_metrics": bench_metrics,
        "n_days": len(merged)
    }


if __name__ == "__main__":
    result = analyze_fund_pair(esg_scheme_code=119709, benchmark_scheme_code=120716, years=5)

    print(f"ESG Fund: {result['esg_name']}")
    print(f"Benchmark: {result['bench_name']}")
    print(f"Aligned trading days: {result['n_days']}\n")

    print("--- ESG Fund Metrics ---")
    for k, v in result['esg_metrics'].items():
        print(f"  {k}: {v:.4f}")

    print("\n--- Benchmark Metrics ---")
    for k, v in result['bench_metrics'].items():
        print(f"  {k}: {v:.4f}")