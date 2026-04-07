"""Data agent."""

from app.skills.financial_data_skills import collect_financial_context


class DataAgent:
    """Fetches financial and company data from services and repositories."""

    def run(self, ticker: str = "") -> dict[str, object]:
        return collect_financial_context(ticker)
