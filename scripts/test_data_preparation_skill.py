from __future__ import annotations

"""用于联调 DataPreparationSkill 的最小测试脚本。

使用前请根据你自己的项目实际路径，重点确认：
1. SessionLocal / 数据库 session 工厂 的导入路径
2. app.domain.models.TimeRange 的字段名是否与这里一致
3. CompanyRepository / 各 Repo / TushareService 的初始化方式是否需要额外参数

推荐放到项目根目录下的 scripts/ 目录中运行。
"""

import pprint
import sys
from pathlib import Path


# 让脚本从 scripts/ 目录运行时也能找到 app/
PROJECT_ROOT = Path(__file__).resolve().parents[0]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.config import settings
from app.core.database import SessionLocal  # 这里如果你的 session 工厂名字不同，需要改
from app.domain.models import TimeRange
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService, TushareServiceConfig
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.data_preparation_skill import DataPreparationSkill


def build_skill() -> DataPreparationSkill:
    """手动装配 DataPreparationSkill 依赖。"""
    company_repo = CompanyRepository()
    income_repo = IncomeRepository()
    balance_repo = BalanceSheetRepository()
    cashflow_repo = CashFlowRepository()
    indicator_repo = FinaIndicatorRepository()
    config = TushareServiceConfig(settings.TuShare_Token)
    tushare_service = TushareService(config)

    company_resolver = CompanyResolver(
        company_repo=company_repo,
        tushare_service=tushare_service,
    )
    time_range_parser = TimeRangeParser()
    data_completeness_checker = DataCompletenessChecker()

    skill = DataPreparationSkill(
        company_resolver=company_resolver,
        time_range_parser=time_range_parser,
        data_completeness_checker=data_completeness_checker,
        income_repo=income_repo,
        indicator_repo=indicator_repo,
        cashflow_repo=cashflow_repo,
        balance_repo=balance_repo,
        tushare_service=tushare_service,
    )
    return skill


def print_result(result) -> None:
    print("\n===== DataPreparationResult =====")
    print(f"ts_code: {result.ts_code}")
    print(f"company_name: {result.company_name}")
    print(f"preparation_status: {result.preparation_status}")
    print(f"message: {result.message}")
    print(f"required_parts: {result.required_parts}")

    print("\n===== Completeness Result =====")
    if result.completeness_result is None:
        print("completeness_result: None")
    else:
        cr = result.completeness_result
        print(f"needs_backfill: {cr.needs_backfill}")
        print(f"has_missing_data: {getattr(cr, 'has_missing_data', None)}")
        print(f"missing_parts: {getattr(cr, 'missing_parts', None)}")
        print(f"expected_periods: {getattr(cr, 'expected_periods', None)}")
        print(f"completeness_reason: {getattr(cr, 'completeness_reason', None)}")

        print("\npart_details:")
        for part_name, detail in cr.part_details.items():
            print(f"  - {part_name}")
            print(f"      is_complete: {detail.is_complete}")
            print(f"      available_periods: {getattr(detail, 'available_periods', None)}")
            print(f"      missing_periods: {getattr(detail, 'missing_periods', None)}")

    print("\n===== Raw Financial Data Count =====")
    for part_name, records in result.raw_financial_data.items():
        print(f"{part_name}: {len(records)}")

    print("\n===== Raw Financial Data Preview =====")
    for part_name, records in result.raw_financial_data.items():
        print(f"\n--- {part_name} ---")
        if not records:
            print("[]")
            continue
        preview = records[:2] if isinstance(records, list) else records
        pprint.pprint(preview)


def main() -> None:
    db = SessionLocal()
    try:
        skill = build_skill()

        # 这里优先走“只给公司名”的场景，顺便覆盖 company_resolver
        company_name = "宁德时代"
        ts_code = None

        # 你如果 TimeRange 的字段不是这些，请按你的真实 dataclass 改
        time_range = TimeRange(
            start_year=2023,
            start_month=1,
            end_year=2025,
            end_month=12,
        )

        required_parts = settings.CORE_FINANCIAL_PARTS.copy()
        # 你也可以先缩小范围单测，例如：
        # required_parts = ["income_statements", "financial_indicators"]

        print("===== INPUT =====")
        print(f"company_name: {company_name}")
        print(f"ts_code: {ts_code}")
        print(f"time_range: {time_range}")
        print(f"required_parts: {required_parts}")

        result = skill.prepare(
            db=db,
            ts_code=ts_code,
            company_name=company_name,
            time_range=time_range,
            required_parts=required_parts,
            backfill={
                "income_statements": ['2023-03-31', '2023-06-30', '2023-09-30', '2023-12-31', '2024-03-31', '2024-06-30', '2024-09-30', '2024-12-31', '2025-03-31', '2025-06-30', '2025-09-30', '2025-12-31'],
            }
        )

        db.commit()

        print_result(result)

    except Exception as e:
        print("\n===== TEST FAILED =====")
        print(type(e).__name__, str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
