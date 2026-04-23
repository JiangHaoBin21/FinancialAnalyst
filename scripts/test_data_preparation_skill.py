from __future__ import annotations

import sys
from pathlib import Path
from pprint import pprint


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.models import TimeRange
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService, TushareServiceConfig
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.data.company_profile_fetch_skill import CompanyProfileFetchSkill
from app.skills.data.data_preparation_skill import DataPreparationSkill


def build_company_profile_skill(tushare_service: TushareService) -> CompanyProfileFetchSkill:
    company_resolver = CompanyResolver(
        company_repo=CompanyRepository(),
        tushare_service=tushare_service,
    )
    return CompanyProfileFetchSkill(
        company_resolver=company_resolver,
        session_factory=SessionLocal,
    )


def build_data_preparation_skill(tushare_service: TushareService) -> DataPreparationSkill:
    return DataPreparationSkill(
        time_range_parser=TimeRangeParser(),
        income_repo=IncomeRepository(),
        indicator_repo=FinaIndicatorRepository(),
        cashflow_repo=CashFlowRepository(),
        balance_repo=BalanceSheetRepository(),
        tushare_service=tushare_service,
        session_factory=SessionLocal,
    )


def preview_records(records: list[dict], limit: int = 2) -> None:
    print(f"record_count: {len(records)}")
    if not records:
        print("preview: []")
        return

    preview_fields = (
        "ts_code",
        "end_date",
        "ann_date",
        "report_type",
        "revenue",
        "total_revenue",
        "roe",
        "gross_margin",
        "debt_to_assets",
    )
    preview = [
        {field: record.get(field) for field in preview_fields if field in record}
        for record in records[:limit]
    ]
    pprint(preview)


def main() -> None:
    tushare_service = TushareService(TushareServiceConfig(token=settings.TuShare_Token))
    company_profile_skill = build_company_profile_skill(tushare_service)
    data_preparation_skill = build_data_preparation_skill(tushare_service)

    company_name = None
    ts_code = "300750.SZ"
    time_range = TimeRange(
        start_year=2023,
        start_month=1,
        end_year=2025,
        end_month=12,
    )
    required_parts = [
        "income_statements",
        "financial_indicators",
    ]

    print("===== INPUT =====")
    print(f"company_name: {company_name}")
    print(f"ts_code: {ts_code}")
    print(f"time_range: {time_range}")
    print(f"required_parts: {required_parts}")

    print("\n===== STEP 1: Fetch company profile =====")
    company_profile = company_profile_skill.fetch(company_name, ts_code)
    pprint(company_profile)

    print("\n===== STEP 2: Load local data through DataPreparationSkill =====")
    for part_name in required_parts:
        print(f"\n--- {part_name} ---")
        records = data_preparation_skill.prepare(
            time_range=time_range,
            required_parts=[part_name],
            company_profile=company_profile,
        )
        preview_records(records)

    print("\n===== DONE =====")
    print("DataPreparationSkill script completed successfully.")


if __name__ == "__main__":
    main()
