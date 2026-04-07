"""Skills for financial data collection."""

from app.tools.financial_data_tools import fetch_company_profile


def collect_financial_context(ticker: str) -> dict[str, object]:
    """Build a minimal financial context for downstream agents."""
    profile = fetch_company_profile(ticker or "UNKNOWN")
    return {"ticker": profile["ticker"], "profile": profile}
