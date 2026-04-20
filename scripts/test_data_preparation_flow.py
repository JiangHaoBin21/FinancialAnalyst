# scripts/test_data_preparation_flow.py
from __future__ import annotations

from pprint import pprint

from app.core.config import settings
from app.core.database import SessionLocal  # 按你的真实路径修改
from app.services.tushare_service import TushareService, TushareServiceConfig

from app.repositories.company_repo import CompanyRepository
from app.repositories.indicator_repo import FinaIndicatorRepository  # 按你的真实类名修改

from app.domain.models import TimeRange  # 按你的真实路径修改
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker


def main() -> None:
    # ========= 1) 基础依赖 =========
    db = SessionLocal()

    tushare_service = TushareService(
        TushareServiceConfig(token=settings.TuShare_Token)
    )

    company_repo = CompanyRepository()
    indicator_repo = FinaIndicatorRepository()  # 按你的真实类名修改

    company_resolver = CompanyResolver(
        company_repo=company_repo,
        tushare_service=tushare_service,
    )
    time_range_parser = TimeRangeParser()
    completeness_checker = DataCompletenessChecker()

    try:
        # ========= 2) 输入 =========
        company_name = "宁德时代"
        ts_code = None
        time_range = TimeRange(
            start_year=2022,
            start_month=1,
            end_year=2024,
            end_month=12,
        )

        print("\n===== STEP 1: Resolve company =====")
        company_profile = company_resolver.resolve(
            db=db,
            company_name=company_name,
            ts_code=ts_code,
        )
        pprint(company_profile)
        company_source = company_profile.get("source")
        print("company_source =", company_source)

        print("\n===== STEP 2: Parse time range =====")
        parsed_range = time_range_parser.parse(time_range)
        # 这里假设你 ParsedTimeRange 有下面这些字段
        print("start_date_obj =", parsed_range.start_date_obj)
        print("end_date_obj   =", parsed_range.end_date_obj)
        print("start_date_str =", parsed_range.start_date_str)
        print("end_date_str   =", parsed_range.end_date_str)

        print("\n===== STEP 3: Query local fina_indicator =====")
        # 这里的方法名按你的 repo 实际接口改
        local_indicators = indicator_repo.list_by_ts_code_and_date_range(
            db=db,
            ts_code=company_profile["ts_code"],
            start_date=parsed_range.start_date_obj,
            end_date=parsed_range.end_date_obj,
        )

        print(f"local_indicators count = {len(local_indicators)}")

        local_financial_data = {
            "income_statements": [],
            "balance_sheets": [],
            "cashflow_statements": [],
            "financial_indicators": local_indicators,
        }

        print("\n===== STEP 4: Check completeness =====")
        completeness = completeness_checker.check(
            requested_time_range=time_range,
            financial_data=local_financial_data,
        )
        pprint(completeness)

        print("\n===== STEP 5: Fetch from tushare if needed =====")
        if completeness.needs_backfill:
            fetched_indicator_records = tushare_service.get_fina_indicator_records(
                ts_code=company_profile["ts_code"],
                start_date=parsed_range.start_date_str,
                end_date=parsed_range.end_date_str,
            )
            print(f"fetched_indicator_records count = {len(fetched_indicator_records)}")
            print(fetched_indicator_records)

            print("\n===== STEP 6: Persist fetched records =====")
            # 这里的方法名按你的 repo 实际接口改
            # 如果你没有 bulk_upsert，就先循环 upsert
            indicator_repo.bulk_upsert(db=db, data=fetched_indicator_records)

            db.commit()
            print("persist success")

        else:
            print("local data is sufficient, skip tushare fetch")

        print("\n===== STEP 7: Re-query from DB for verification =====")
        final_indicators = indicator_repo.list_by_ts_code_and_date_range(
            db=db,
            ts_code=company_profile["ts_code"],
            start_date=parsed_range.start_date_obj,
            end_date=parsed_range.end_date_obj,
        )

        print(f"final_indicators count = {len(final_indicators)}")

        if final_indicators:
            sample = final_indicators[0]
            print({
                "ts_code": sample.ts_code,
                "end_date": sample.end_date,
                "ann_date": sample.ann_date,
                "roe": sample.roe,
                "gross_margin": sample.gross_margin,
                "debt_to_assets": sample.debt_to_assets,
                "source": sample.source,
            })

        print("\nFetched end_dates:")
        print([r["end_date"] for r in fetched_indicator_records])

        print("\nFetched distinct end_dates:")
        print(sorted({r["end_date"] for r in fetched_indicator_records}))

        print("\nFinal DB end_dates:")
        print([x.end_date for x in final_indicators])

        print("\n===== DONE =====")
        print("Minimal data flow test completed successfully.")

    except Exception as e:
        db.rollback()
        print("\n===== ERROR =====")
        print(repr(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()