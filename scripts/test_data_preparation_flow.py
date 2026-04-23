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
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.data.company_profile_fetch_skill import CompanyProfileFetchSkill
from app.skills.data.completeness_check_skill import CompletenessCheckSkill
from app.skills.data.data_preparation_skill import DataPreparationSkill


def build_skills() -> tuple[CompanyProfileFetchSkill, DataPreparationSkill, CompletenessCheckSkill]:
    company_repo = CompanyRepository()
    income_repo = IncomeRepository()
    balance_repo = BalanceSheetRepository()
    cashflow_repo = CashFlowRepository()
    indicator_repo = FinaIndicatorRepository()

    tushare_service = TushareService(TushareServiceConfig(token=settings.TuShare_Token))
    company_resolver = CompanyResolver(
        company_repo=company_repo,
        tushare_service=tushare_service,
    )

    company_profile_fetch_skill = CompanyProfileFetchSkill(
        company_resolver=company_resolver,
        session_factory=SessionLocal,
    )
    data_preparation_skill = DataPreparationSkill(
        time_range_parser=TimeRangeParser(),
        income_repo=income_repo,
        indicator_repo=indicator_repo,
        cashflow_repo=cashflow_repo,
        balance_repo=balance_repo,
        tushare_service=tushare_service,
        session_factory=SessionLocal,
    )
    completeness_check_skill = CompletenessCheckSkill(DataCompletenessChecker())
    return company_profile_fetch_skill, data_preparation_skill, completeness_check_skill


def load_financial_data(
    skill: DataPreparationSkill,
    *,
    company_profile: dict,
    time_range: TimeRange,
    required_parts: list[str],
) -> dict[str, list[dict]]:
    financial_data: dict[str, list[dict]] = {}
    for part_name in required_parts:
        financial_data[part_name] = skill.prepare(
            time_range=time_range,
            required_parts=[part_name],
            company_profile=company_profile,
        )
    return financial_data


def build_backfill_plan(check_result: dict) -> dict[str, list[str]]:
    plan: dict[str, list[str]] = {}
    for detail in check_result.get("part_details", []):
        missing_periods = detail.get("missing_periods") or []
        if missing_periods:
            plan[detail["part_name"]] = missing_periods
    return plan


def print_data_summary(financial_data: dict[str, list[dict]]) -> None:
    print("\n===== Financial Data Summary =====")
    for part_name, records in financial_data.items():
        periods = sorted(
            {
                str(record.get("end_date"))
                for record in records
                if record.get("end_date") is not None
            }
        )
        print(f"{part_name}: count={len(records)}, periods={periods}")


def main() -> None:
    company_profile_fetch_skill, data_preparation_skill, completeness_check_skill = build_skills()

    company_name = None
    ts_code = "300750.SZ"
    time_range = TimeRange(
        start_year=2022,
        start_month=1,
        end_year=2024,
        end_month=12,
    )
    required_parts = ["financial_indicators"]

    print("===== INPUT =====")
    print(f"company_name: {company_name}")
    print(f"ts_code: {ts_code}")
    print(f"time_range: {time_range}")
    print(f"required_parts: {required_parts}")

    print("\n===== STEP 1: Fetch company profile =====")
    company_profile = company_profile_fetch_skill.fetch(company_name, ts_code)
    pprint(company_profile)

    print("\n===== STEP 2: Load local financial data =====")
    financial_data = load_financial_data(
        data_preparation_skill,
        company_profile=company_profile,
        time_range=time_range,
        required_parts=required_parts,
    )
    print_data_summary(financial_data)

    print("\n===== STEP 3: Check completeness =====")
    completeness = completeness_check_skill.skill_check(
        requested_time_range=time_range,
        financial_data=financial_data,
        required_parts=required_parts,
    )
    pprint(completeness)

    backfill_plan = build_backfill_plan(completeness)
    if backfill_plan:
        print("\n===== STEP 4: Backfill missing periods =====")
        pprint(backfill_plan)
        fetched_records = data_preparation_skill.prepare(
            time_range=time_range,
            required_parts=required_parts,
            company_profile=company_profile,
            backfill=backfill_plan,
        )
        print(f"backfilled records: {len(fetched_records)}")

        print("\n===== STEP 5: Re-load and re-check =====")
        financial_data = load_financial_data(
            data_preparation_skill,
            company_profile=company_profile,
            time_range=time_range,
            required_parts=required_parts,
        )
        print_data_summary(financial_data)
        completeness = completeness_check_skill.skill_check(
            requested_time_range=time_range,
            financial_data=financial_data,
            required_parts=required_parts,
        )
        pprint(completeness)
    else:
        print("\n===== STEP 4: Backfill skipped =====")
        print("local data is complete for requested parts and range")

    print("\n===== DONE =====")
    print("Data preparation flow script completed successfully.")


if __name__ == "__main__":
    main()
