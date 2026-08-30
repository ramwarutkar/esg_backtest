import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_analyst_summary(fund_results, anova_result=None):
    """
    Takes ALREADY-COMPUTED statistics (t-test and, if available, ANOVA
    results) and asks an LLM to narrate them in plain English. The model
    is explicitly instructed to only reference the numbers it's given,
    never invent new ones. anova_result is None when only one fund was
    analyzed, since ANOVA needs multiple groups to compare.
    """

    # Build a clean, explicit data block the model can't misread
    fund_lines = []
    for r in fund_results:
        fund_lines.append(
            f"- {r['fund_name']}: Sharpe diff vs benchmark = {r['sharpe_diff']:+.4f}, "
            f"t-test p-value = {r['p_value']:.4f}, "
            f"significant at 5%? {'Yes' if r['significant'] else 'No'}"
        )
    fund_data_block = "\n".join(fund_lines)

    if anova_result is not None:
        anova_block = (
            f"One-way ANOVA across all {len(fund_results)} funds' daily excess returns: "
            f"F-statistic = {anova_result['f_statistic']:.4f}, "
            f"p-value = {anova_result['p_value']:.4f}, "
            f"significant at 5%? {'Yes' if anova_result['significant_at_5pct'] else 'No'}"
        )
    else:
        anova_block = (
            "Only one fund was analyzed, so no ANOVA (cross-fund comparison) was run. "
            "Do not mention ANOVA or cross-fund consistency in the summary."
        )

    prompt = f"""You are a quantitative research analyst writing a short findings summary for
a portfolio performance study comparing ESG-screened Indian mutual funds against the
Nifty 50 benchmark.

STRICT RULES:
- Only reference the numbers provided below. Do not invent, estimate, or round to a
  different value than what is given.
- Do not claim a result is significant if the data says it is not, or vice versa.
- Be direct and precise, like a real research note — not promotional or vague.
- Keep it to 4-6 sentences.
- If the results are mixed or show no clear effect, say so plainly rather than
  forcing a conclusion.

DATA — per-fund t-test results:
{fund_data_block}

DATA — ANOVA across funds:
{anova_block}

Write the findings summary:"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # low temperature: we want precise, consistent narration, not creativity
        max_completion_tokens=700,  # room for both reasoning and the final answer
        reasoning_effort="low"  # this task needs precision, not deep deliberation
    )

    return response.choices[0].message.content


def generate_single_fund_summary(fund_result):
    """
    Narrates ONE fund's result in 1-2 sentences. Used when displaying each
    fund's own block, separate from the cross-fund Overall Summary.
    """
    prompt = f"""You are a quantitative research analyst. Write a 1-2 sentence summary of
this single fund's performance versus its benchmark, using ONLY the numbers below.
Do not invent figures. Do not mention other funds or ANOVA. Be direct and precise.

Fund: {fund_result['fund_name']}
Sharpe (fund): {fund_result['sharpe_esg']:.4f}
Sharpe (benchmark): {fund_result['sharpe_bench']:.4f}
Sharpe difference: {fund_result['sharpe_diff']:+.4f}
CAGR (fund): {fund_result['cagr_esg']*100:.2f}%
CAGR (benchmark): {fund_result['cagr_bench']*100:.2f}%
Paired t-test p-value: {fund_result['p_value']:.4f}
Statistically significant at 5%: {'Yes' if fund_result['significant'] else 'No'}

Write the summary:"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=400,
        reasoning_effort="low"
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Using your ACTUAL results from the real backtest, hardcoded here for testing
    fund_results = [
        {"fund_name": "SBI ESG Exclusionary Strategy Fund", "sharpe_diff": 0.0717, "p_value": 0.5896, "significant": False},
        {"fund_name": "ICICI Prudential ESG Exclusionary Strategy Fund", "sharpe_diff": 0.0975, "p_value": 0.7367, "significant": False},
        {"fund_name": "Axis ESG Integration Strategy Fund", "sharpe_diff": -0.1241, "p_value": 0.5397, "significant": False},
    ]

    anova_result = {"f_statistic": 0.3939, "p_value": 0.6745, "significant_at_5pct": False}

    summary = generate_analyst_summary(fund_results, anova_result)
    print(summary)