from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import numpy as np
from run_full_analysis import run_full_pipeline, ESG_FUNDS, BENCHMARK_CODE, BENCHMARK_NAME

app = FastAPI(title="Parity — ESG Portfolio Backtest API")

_cache = {}


def convert_numpy_types(obj):
    """Recursively converts NumPy scalar types into native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


@app.get("/")
def root():
    return {"message": "Parity ESG Backtest API is running. Visit /docs for interactive documentation."}


@app.get("/funds")
def list_funds():
    """Returns the available ESG funds and the benchmark they're compared against."""
    return {
        "esg_funds": ESG_FUNDS,
        "benchmark_code": BENCHMARK_CODE,
        "benchmark_name": BENCHMARK_NAME
    }


@app.get("/analysis")
def get_analysis(
    years: int = 5,
    funds: Optional[List[str]] = Query(default=None, description="Fund names to include. Omit to include all.")
):
    """
    Runs the full pipeline for the SELECTED funds only (or all funds if
    none specified): fetches live NAV data, computes metrics, runs
    t-tests + ANOVA (if 2+ funds), and generates the AI analyst summary.
    """
    if funds:
        invalid = [f for f in funds if f not in ESG_FUNDS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown fund(s): {invalid}")
        selected_funds = {f: ESG_FUNDS[f] for f in funds}
    else:
        selected_funds = ESG_FUNDS

    cache_key = f"years_{years}_funds_{'_'.join(sorted(selected_funds.keys()))}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        result = run_full_pipeline(selected_funds, BENCHMARK_CODE, years=years)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    clean_result = convert_numpy_types(result)

    _cache[cache_key] = clean_result
    return clean_result