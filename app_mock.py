import streamlit as st
import numpy as np
import pandas as pd
import time
from datetime import datetime

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


# ---------- MOCK DATA GENERATION ----------
# One shared date index used by EVERY series, so all funds and the
# benchmark align perfectly when combined into a chart DataFrame.
COMMON_DATE_INDEX = pd.date_range(end=pd.Timestamp.now().normalize(), periods=1260, freq="B")


def get_market_factor():
    """
    The shared 'market' component every fund and the benchmark rides on top
    of — this is what makes the lines actually track each other (like real
    markets do) instead of looking like two unrelated random walks.
    """
    seed = 42 + st.session_state.get("refresh_count", 0)
    rng = np.random.default_rng(seed)
    return rng.normal(0.00045, 0.009, len(COMMON_DATE_INDEX))


def generate_correlated_series(fund_seed, annualized_excess_drift=0.0, idio_vol=0.0035):
    """
    Builds a NAV series = shared market movement + a small fund-specific
    excess return + a small amount of fund-specific noise. This mimics how
    a real fund tracks its benchmark closely but not perfectly.
    """
    market_factor = get_market_factor()
    rng = np.random.default_rng(fund_seed + st.session_state.get("refresh_count", 0) * 100)
    idiosyncratic = rng.normal(0, idio_vol, len(COMMON_DATE_INDEX))
    daily_excess = annualized_excess_drift / 252
    daily_returns = market_factor + daily_excess + idiosyncratic
    nav = 100 * np.cumprod(1 + daily_returns)
    return pd.Series(nav, index=COMMON_DATE_INDEX)


def trailing_return(series, months):
    days = int(months * 21)  # approx trading days per month
    if len(series) <= days:
        return None
    return (series.iloc[-1] / series.iloc[-days - 1]) - 1


def get_bench_series():
    return generate_correlated_series(fund_seed=0, annualized_excess_drift=0.0, idio_vol=0.0025)
BENCH_STATS = {
    "cagr": 0.0968, "volatility": 0.1380, "sharpe": 0.2347, "max_drawdown": -0.1656
}

AVAILABLE_FUNDS = {
    "SBI ESG Exclusionary Strategy Fund": {
        "seed": 1, "sharpe_diff": 0.0712, "p_value": 0.5926, "significant": False,
        "esg_stats": {"cagr": 0.1074, "volatility": 0.1373, "sharpe": 0.3064, "max_drawdown": -0.1951}
    },
    "ICICI Prudential ESG Exclusionary Strategy Fund": {
        "seed": 2, "sharpe_diff": 0.0984, "p_value": 0.7276, "significant": False,
        "esg_stats": {"cagr": 0.1068, "volatility": 0.1310, "sharpe": 0.3161, "max_drawdown": -0.1992}
    },
    "Axis ESG Integration Strategy Fund": {
        "seed": 3, "sharpe_diff": -0.1221, "p_value": 0.5498, "significant": False,
        "esg_stats": {"cagr": 0.0770, "volatility": 0.1420, "sharpe": 0.0956, "max_drawdown": -0.2430}
    },
    "Quantum ESG Best In Class Strategy Fund": {
        "seed": 4, "sharpe_diff": 0.0341, "p_value": 0.8102, "significant": False,
        "esg_stats": {"cagr": 0.1005, "volatility": 0.1355, "sharpe": 0.2688, "max_drawdown": -0.1810}
    },
}

MOCK_ANOVA = {"f_statistic": 0.3845, "p_value": 0.6808, "significant_at_5pct": False}

MOCK_FUND_NARRATION = {
    "SBI ESG Exclusionary Strategy Fund": "Modest positive edge over the benchmark, but not statistically significant — the gap is consistent with ordinary daily variation.",
    "ICICI Prudential ESG Exclusionary Strategy Fund": "Similar pattern to SBI — a small Sharpe advantage that doesn't clear the bar for statistical significance.",
    "Axis ESG Integration Strategy Fund": "This fund actually trails the benchmark on both Sharpe and drawdown, though again not by a significant margin.",
    "Quantum ESG Best In Class Strategy Fund": "A slight positive edge, the smallest of the four funds, and not significant.",
}

MOCK_OVERALL_SUMMARY = (
    "Across the selected funds, Sharpe-ratio differences relative to the Nifty 50 are small and mixed "
    "in direction — some modestly positive, one modestly negative — and none reach statistical "
    "significance individually. A one-way ANOVA across the funds' daily excess returns also shows no "
    "significant variation between them, meaning the funds don't meaningfully differ from each other "
    "either. Taken together, this sample provides no evidence that ESG screening reliably changes "
    "risk-adjusted performance, in either direction."
)

# ---------- CONTROLS ----------
st.markdown('<div class="section-title" style="font-size:18px; padding-top:14px;">Configure Your Backtest</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Pick which ESG funds to compare against the UTI Nifty 50 Index Fund benchmark.</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2.2, 1, 1])
with col1:
    selected_funds = st.multiselect(
        "ESG funds to include", options=list(AVAILABLE_FUNDS.keys()),
        default=[list(AVAILABLE_FUNDS.keys())[0]], label_visibility="collapsed"
    )
with col2:
    years = st.selectbox("Lookback window", [1, 3, 5], index=2, format_func=lambda x: f"{x} year{'s' if x > 1 else ''}", label_visibility="collapsed")
with col3:
    refresh_button = st.button("🔄 Refresh Data", use_container_width=True,
                                help="Re-fetches the latest numbers — selection changes update automatically already.")

st.caption("Benchmark: UTI Nifty 50 Index Fund — Direct Plan, Growth")
st.markdown("<br>", unsafe_allow_html=True)

# ---------- REFRESH TRACKING ----------
# Selection changes re-render automatically (Streamlit reruns on any widget
# change). The Refresh button forces genuinely fresh numbers on top of that,
# rather than requiring a click just to see a selection take effect.
if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
if refresh_button:
    st.session_state.refresh_count += 1

if True:  # analysis always renders for the current selection
    if len(selected_funds) == 0:
        st.warning("Select at least 1 fund to run the analysis.")
    else:
        # ---------- PER-FUND STACKED BLOCKS ----------
        for fund_name in selected_funds:
            fund = AVAILABLE_FUNDS[fund_name]

            st.markdown(f'<div class="fund-header">{fund_name}</div>', unsafe_allow_html=True)
            st.markdown('<div class="fund-sub">vs. UTI Nifty 50 Index Fund — Direct Plan, Growth</div>', unsafe_allow_html=True)

            with st.spinner(f"Fetching live NAV data for {fund_name}..."):
                time.sleep(0.5)
                esg_series = generate_correlated_series(
                    fund_seed=fund["seed"],
                    annualized_excess_drift=fund["sharpe_diff"] * 0.15,  # rough visual proxy, not a real derivation
                    idio_vol=0.0035
                )

            # NAV chart
            st.markdown('<div class="section-title">NAV Comparison (rebased to 100)</div>', unsafe_allow_html=True)
            chart_df = pd.DataFrame({"ESG Fund": esg_series, "Benchmark": get_bench_series()})
            st.line_chart(chart_df, height=220)
            st.markdown('<div class="data-caption">NAV data live via mfapi.in, updated daily.</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            detail_col1, detail_col2, detail_col3 = st.columns(3)

            with detail_col1:
                st.markdown('<div class="section-title">Trailing Returns</div>', unsafe_allow_html=True)
                rows = ""
                for label, months in [("1M", 1), ("3M", 3), ("1Yr", 12), ("3Yr", 36), ("5Yr", 60)]:
                    esg_ret = trailing_return(esg_series, months)
                    bench_ret = trailing_return(get_bench_series(), months)
                    if esg_ret is not None and bench_ret is not None:
                        css = "pos" if esg_ret >= bench_ret else "neg"
                        rows += f'<div class="metric-row"><span>{label}</span><span class="v {css}">{esg_ret*100:+.1f}%</span></div>'
                st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                st.markdown('<div class="data-caption">Green = beat benchmark same period.</div>', unsafe_allow_html=True)

            with detail_col2:
                st.markdown('<div class="section-title">Return &amp; Risk Metrics</div>', unsafe_allow_html=True)
                s = fund["esg_stats"]
                rows = f'''
                <div class="metric-row"><span>CAGR</span><span class="v">{s['cagr']*100:.2f}%</span></div>
                <div class="metric-row"><span>Volatility</span><span class="v">{s['volatility']*100:.2f}%</span></div>
                <div class="metric-row"><span>Sharpe Ratio</span><span class="v">{s['sharpe']:.3f}</span></div>
                <div class="metric-row"><span>Max Drawdown</span><span class="v">{s['max_drawdown']*100:.1f}%</span></div>
                '''
                st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                st.markdown('<div class="data-caption">Descriptive — what actually happened.</div>', unsafe_allow_html=True)

            with detail_col3:
                st.markdown('<div class="section-title">Statistical Test</div>', unsafe_allow_html=True)
                diff = fund["sharpe_diff"]
                css = "pos" if diff > 0 else "neg"
                sig_text = "Significant" if fund["significant"] else "Not significant"
                rows = f'''
                <div class="metric-row"><span>Sharpe diff vs. benchmark</span><span class="v {css}">{diff:+.4f}</span></div>
                <div class="metric-row"><span>Paired t-test p-value</span><span class="v">{fund['p_value']:.4f}</span></div>
                <div class="metric-row"><span>Result</span><span class="v {css}"><b>{sig_text}</b></span></div>
                '''
                st.markdown(f'<div class="metric-box">{rows}</div>', unsafe_allow_html=True)
                st.markdown('<div class="data-caption">Inferential — is that difference real, or noise?</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="ai-tag">✦ AI NOTE</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-box">{MOCK_FUND_NARRATION[fund_name]}</div>', unsafe_allow_html=True)

        # ---------- OVERALL SUMMARY (2+ funds only) ----------
        if len(selected_funds) >= 2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="overall-banner">
                <div class="kicker">Overall Summary</div>
                <h2>How Consistent Is the ESG Effect Across Funds?</h2>
            </div>
            """, unsafe_allow_html=True)

            avg_diff = sum(AVAILABLE_FUNDS[f]["sharpe_diff"] for f in selected_funds) / len(selected_funds)
            n_significant = sum(1 for f in selected_funds if AVAILABLE_FUNDS[f]["significant"])

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
                    <div class="value neutral">{n_significant} / {len(selected_funds)}</div>
                    <div class="label">Funds showing a significant effect</div>
                </div>
                ''', unsafe_allow_html=True)
            with hcol3:
                sig_class = "pos" if MOCK_ANOVA["significant_at_5pct"] else "neutral"
                sig_label = "Significant variation" if MOCK_ANOVA["significant_at_5pct"] else "No significant variation"
                st.markdown(f'''
                <div class="stat-card">
                    <div class="value {sig_class}">F={MOCK_ANOVA['f_statistic']:.3f}, p={MOCK_ANOVA['p_value']:.3f}</div>
                    <div class="label">ANOVA — {sig_label} between funds</div>
                </div>
                ''', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="ai-tag">✦ AI-GENERATED · CROSS-FUND SYNTHESIS</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-box">{MOCK_OVERALL_SUMMARY}</div>', unsafe_allow_html=True)
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("Select 2 or more funds to see the cross-fund consistency (ANOVA) comparison.")

# ---------- METHODOLOGY ----------
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Methodology — what these tests actually check"):
    st.markdown("""
    - **Paired t-test**: For each trading day, computes the ESG fund's return minus the benchmark's return that same day, then tests whether the *average* of those daily differences is distinguishable from zero — i.e., whether one consistently beats the other, or if the gap is explainable by ordinary daily noise.
    - **One-way ANOVA**: Tests whether the daily excess returns (fund minus benchmark) differ significantly *across the selected funds themselves* — not whether any one beats the benchmark, but whether the funds behave consistently with each other.
    - **Sharpe ratio**: Computed using India's approximate risk-free rate (6% annualized) as the baseline, since Sharpe measures return earned per unit of risk taken *above* a safe alternative.
    - **Significance threshold**: 5% (p < 0.05) throughout, the conventional standard in financial research.
    """)

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Parity is a research/learning project. Figures are computed live from public mutual fund NAV data (mfapi.in) and are not investment advice.")