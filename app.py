import streamlit as st
import requests
import pandas as pd
from datetime import datetime

#API_URL = "http://localhost:8000"
API_URL = "https://esg-backtest.onrender.com/"


def trailing_return_from_series(values, months):
    """Computes trailing return from a list of rebased NAV values, using ~21 trading days/month."""
    days = int(months * 21)
    if len(values) <= days:
        return None
    return (values[-1] / values[-days - 1]) - 1

st.set_page_config(page_title="Parity — ESG Portfolio Backtest", page_icon="📊", layout="wide")

# ---------- FONTS ----------
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ---------- CSS ----------
st.markdown("""
<style>
html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

.masthead { padding: 26px 0 20px 0; border-bottom: 2px solid #122B4D; margin-bottom: 4px; }
.masthead-kicker { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #96702C;
    letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 10px; }
.masthead h1 { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 32px; color: #122B4D; margin: 0 0 8px 0; }
.masthead p { color: #5B6472; font-size: 13.5px; max-width: 680px; line-height: 1.6; margin: 0; }

.fund-header { font-family: 'Source Serif 4', serif; font-size: 20px; font-weight: 600; color: #122B4D;
    margin: 6px 0 2px 0; padding-top: 18px; border-top: 1px solid #E4E3DD; }
.fund-sub { font-size: 11.5px; color: #9A9E97; margin-bottom: 14px; }

.section-title { font-family: 'Source Serif 4', serif; font-size: 15px; font-weight: 600; color: #122B4D; margin: 4px 0 8px 0; }
.section-desc { font-size: 11.5px; color: #6B7280; margin-bottom: 10px; }

.metric-box { border: 1px solid #DDE1E6; border-radius: 8px; padding: 14px 16px; background: white; height: 100%; }
.metric-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #EFEFEA; font-size: 12.5px; }
.metric-row:last-child { border-bottom: none; }
.metric-row .v { font-family: 'IBM Plex Mono', monospace; }
.pos { color: #1E6B4F; } .neg { color: #9C3B2E; } .neutral { color: #122B4D; }

.stat-card { border: 1px solid #DDE1E6; border-radius: 8px; padding: 16px; background: white; text-align: center; min-height: 100px;
    display: flex; flex-direction: column; justify-content: center; }
.stat-card .value { font-family: 'IBM Plex Mono', monospace; font-size: 23px; font-weight: 600; }
.stat-card .label { font-size: 11px; color: #6B7280; margin-top: 6px; line-height: 1.5; }

.ai-box { background: linear-gradient(135deg, #FFFFFF 0%, #F5F3EC 130%); border: 1px solid #E4E3DD;
    border-top: 3px solid #122B4D; padding: 16px 18px; border-radius: 6px; font-size: 13px; line-height: 1.65; color: #1A1D22; }
.ai-tag { font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; background: #122B4D; color: white;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 10px; display: inline-block; letter-spacing: 0.3px; }

.overall-banner { background: #122B4D; color: white; padding: 22px 26px; border-radius: 8px; margin: 10px 0 20px 0; }
.overall-banner .kicker { font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; color: #96702C;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.overall-banner h2 { font-family: 'Source Serif 4', serif; font-size: 20px; font-weight: 600; margin: 0; }

.data-caption { font-size: 10.5px; color: #9A9E97; font-style: italic; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ---------- MASTHEAD ----------
now_str = datetime.now().strftime("%B %d, %Y")
st.markdown(f"""
<div class="masthead">
    <div class="masthead-kicker">Parity Research · Portfolio Analytics</div>
    <h1>Does ESG Screening Cost You Returns?</h1>
    <p>A live, statistically tested backtest of Indian ESG mutual funds against the Nifty 50 —
    computed fresh from public NAV data as of {now_str}, not a static report.</p>
</div>
""", unsafe_allow_html=True)


# ---------- FETCH AVAILABLE FUNDS (real, from backend) ----------
@st.cache_data(ttl=3600)
def get_available_funds():
    response = requests.get(f"{API_URL}/funds", timeout=15)
    response.raise_for_status()
    return response.json()

try:
    funds_meta = get_available_funds()
    ESG_FUND_NAMES = list(funds_meta["esg_funds"].keys())
    BENCHMARK_NAME = funds_meta["benchmark_name"]
except requests.exceptions.RequestException as e:
    st.error(f"Could not reach the backend at {API_URL}. Is it running? ({e})")
    st.stop()

# ---------- CONTROLS ----------
st.markdown('<div class="section-title" style="font-size:18px; padding-top:14px;">Configure Your Backtest</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Pick which ESG funds to compare against the benchmark.</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2.2, 1, 1])
with col1:
    selected_funds = st.multiselect(
        "ESG funds to include", options=ESG_FUND_NAMES,
        default=[ESG_FUND_NAMES[0]], label_visibility="collapsed"
    )
with col2:
    years = st.selectbox("Lookback window", [1, 3, 5], index=2, format_func=lambda x: f"{x} year{'s' if x > 1 else ''}", label_visibility="collapsed")
with col3:
    refresh_button = st.button("🔄 Refresh Data", use_container_width=True,
                                help="Re-fetches live numbers — selection changes update automatically already.")

st.caption(f"Benchmark: {BENCHMARK_NAME}")
st.markdown("<br>", unsafe_allow_html=True)

if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
if refresh_button:
    st.session_state.refresh_count += 1

# ---------- FETCH REAL ANALYSIS ----------
def fetch_analysis(fund_names, years, cache_bust):
    params = [("years", years)] + [("funds", f) for f in fund_names]
    response = requests.get(f"{API_URL}/analysis", params=params, timeout=180)
    if response.status_code != 200:
        raise RuntimeError(f"Server error ({response.status_code}): {response.text}")
    return response.json()


if len(selected_funds) == 0:
    st.warning("Select at least 1 fund to run the analysis.")
else:
    cache_key = f"analysis_{years}_{'_'.join(sorted(selected_funds))}_{st.session_state.refresh_count}"

    if cache_key not in st.session_state:
        with st.spinner("Fetching live fund data and running statistical tests... this can take 30-90 seconds."):
            try:
                st.session_state[cache_key] = fetch_analysis(selected_funds, years, st.session_state.refresh_count)
                st.session_state[f"{cache_key}_error"] = None
            except (requests.exceptions.RequestException, RuntimeError) as e:
                st.session_state[cache_key] = None
                st.session_state[f"{cache_key}_error"] = str(e)

    data = st.session_state.get(cache_key)
    error = st.session_state.get(f"{cache_key}_error")

    if error:
        st.error(error)
    elif data:
        fund_results = data["fund_results"]
        anova_result = data.get("anova_result")
        analyst_summary = data.get("analyst_summary", "")

        # ---------- PER-FUND STACKED BLOCKS ----------
        for fund in fund_results:
            fund_name = fund["fund_name"]

            st.markdown(f'<div class="fund-header">{fund_name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="fund-sub">vs. {BENCHMARK_NAME}</div>', unsafe_allow_html=True)

            # NAV chart from REAL data returned by the backend
            st.markdown('<div class="section-title">NAV Comparison (rebased to 100)</div>', unsafe_allow_html=True)
            nav = fund["nav_series"]
            chart_df = pd.DataFrame({
                "ESG Fund": nav["esg_nav"],
                "Benchmark": nav["bench_nav"]
            }, index=pd.to_datetime(nav["dates"]))
            st.line_chart(chart_df, height=220)
            st.markdown('<div class="data-caption">NAV data live via mfapi.in, updated daily.</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            detail_col1, detail_col2, detail_col3 = st.columns(3)

            with detail_col1:
                st.markdown('<div class="section-title">Trailing Returns</div>', unsafe_allow_html=True)
                rows = ""
                for label, months in [("1M", 1), ("3M", 3), ("1Yr", 12), ("3Yr", 36), ("5Yr", 60)]:
                    esg_ret = trailing_return_from_series(nav["esg_nav"], months)
                    bench_ret = trailing_return_from_series(nav["bench_nav"], months)
                    if esg_ret is not None and bench_ret is not None:
                        css = "pos" if esg_ret >= bench_ret else "neg"
                        rows += f'<div class="metric-row"><span>{label}</span><span class="v {css}">{esg_ret*100:+.1f}%</span></div>'
                if rows:
                    st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="data-caption">Green = beat benchmark same period.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="metric-box">Not enough history for this window.</div>', unsafe_allow_html=True)

            with detail_col2:
                st.markdown('<div class="section-title">Return &amp; Risk Metrics</div>', unsafe_allow_html=True)
                rows = f'''
                <div class="metric-row"><span>CAGR (ESG)</span><span class="v">{fund['cagr_esg']*100:.2f}%</span></div>
                <div class="metric-row"><span>CAGR (Benchmark)</span><span class="v">{fund['cagr_bench']*100:.2f}%</span></div>
                <div class="metric-row"><span>Volatility (ESG)</span><span class="v">{fund['volatility_esg']*100:.2f}%</span></div>
                <div class="metric-row"><span>Max Drawdown (ESG)</span><span class="v">{fund['max_drawdown_esg']*100:.1f}%</span></div>
                '''
                st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                st.markdown('<div class="data-caption">Descriptive — what actually happened.</div>', unsafe_allow_html=True)

            with detail_col3:
                st.markdown('<div class="section-title">Statistical Test</div>', unsafe_allow_html=True)
                diff = fund["sharpe_diff"]
                css = "pos" if diff > 0 else "neg"
                sig_text = "Significant" if fund["significant"] else "Not significant"
                rows = f'''
                <div class="metric-row"><span>Sharpe (ESG)</span><span class="v">{fund['sharpe_esg']:.4f}</span></div>
                <div class="metric-row"><span>Sharpe (Benchmark)</span><span class="v">{fund['sharpe_bench']:.4f}</span></div>
                <div class="metric-row"><span>Sharpe diff</span><span class="v {css}">{diff:+.4f}</span></div>
                <div class="metric-row"><span>Paired t-test p-value</span><span class="v">{fund['p_value']:.4f}</span></div>
                <div class="metric-row"><span>Result</span><span class="v {css}"><b>{sig_text}</b></span></div>
                '''
                st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                st.markdown('<div class="data-caption">Inferential — is that difference real, or noise?</div>', unsafe_allow_html=True)

            if fund.get("fund_summary"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="ai-tag">✦ AI NOTE</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="ai-box">{fund["fund_summary"]}</div>', unsafe_allow_html=True)

        # ---------- OVERALL SUMMARY (2+ funds only) ----------
        if len(fund_results) >= 2 and anova_result:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="overall-banner">
                <div class="kicker">Overall Summary</div>
                <h2>How Consistent Is the ESG Effect Across Funds?</h2>
            </div>
            """, unsafe_allow_html=True)

            avg_diff = sum(f["sharpe_diff"] for f in fund_results) / len(fund_results)
            n_significant = sum(1 for f in fund_results if f["significant"])

            hcol1, hcol2, hcol3 = st.columns(3)
            with hcol1:
                css = "pos" if avg_diff > 0 else "neg"
                st.markdown(f'''
                <div class="stat-card">
                    <div class="value {css}">{avg_diff:+.4f}</div>
                    <div class="label">Average Sharpe diff across selected funds</div>
                </div>
                ''', unsafe_allow_html=True)
            with hcol2:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="value neutral">{n_significant} / {len(fund_results)}</div>
                    <div class="label">Funds showing a significant effect</div>
                </div>
                ''', unsafe_allow_html=True)
            with hcol3:
                sig_class = "pos" if anova_result["significant_at_5pct"] else "neutral"
                sig_label = "Significant variation" if anova_result["significant_at_5pct"] else "No significant variation"
                st.markdown(f'''
                <div class="stat-card">
                    <div class="value {sig_class}">F={anova_result['f_statistic']:.3f}, p={anova_result['p_value']:.3f}</div>
                    <div class="label">ANOVA — {sig_label} between funds</div>
                </div>
                ''', unsafe_allow_html=True)

        if analyst_summary:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="ai-tag">✦ AI-GENERATED · CROSS-FUND SYNTHESIS</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-box">{analyst_summary}</div>', unsafe_allow_html=True)

# ---------- METHODOLOGY ----------
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Methodology — what these tests actually check"):
    st.markdown("""
    - **Paired t-test**: For each trading day, computes the ESG fund's return minus the benchmark's return that same day, then tests whether the *average* of those daily differences is distinguishable from zero.
    - **One-way ANOVA**: Tests whether the daily excess returns (fund minus benchmark) differ significantly *across the selected funds themselves*.
    - **Sharpe ratio**: Computed using India's approximate risk-free rate (6% annualized) as the baseline.
    - **Significance threshold**: 5% (p < 0.05) throughout.
    """)

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Parity is a research/learning project. Figures are computed live from public mutual fund NAV data (mfapi.in) and are not investment advice.")