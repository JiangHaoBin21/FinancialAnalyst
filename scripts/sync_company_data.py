"""Synchronize company master data."""

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tushare_service import TushareService


def main() -> None:
    """Run the company sync placeholder."""
    service = TushareService()
    print(service.fetch_company_profile("DEMO"))


if __name__ == "__main__":
    main()
