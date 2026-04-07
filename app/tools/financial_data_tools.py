"""Tools for financial data access."""

from app.services.tushare_service import TushareService


def fetch_company_profile(ticker: str) -> dict[str, str]:
    """Fetch a lightweight company profile."""
    service = TushareService()
    return service.fetch_company_profile(ticker)
