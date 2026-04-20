"""原始数据数据准备skill"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domain.models import TimeRange, DataPreparationResult
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.helpers import get_repo_or_func_from_part_name, get_records_from_date_and_required_parts
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.capabilities.data_summary_builder import DataSummaryBuilder
from app.core.config import settings


class DataPreparationSkill:
    """
    数据准备 Skill

    职责：
    1. 解析目标公司
    2. 解析时间范围
    3. 优先从本地库查询财务数据
    4. 判断数据是否完整
    5. 必要时回源 TuShare 并落库
    6. 组装标准化财务数据和摘要

    不负责：
    - 读写 WorkflowState
    - 控制 graph / node 流程
    - 财务分析
    - 报告生成
    """

    def __init__(
        self,
        company_resolver: CompanyResolver,
        time_range_parser: TimeRangeParser,
        data_completeness_checker: DataCompletenessChecker,

        income_repo: IncomeRepository,
        indicator_repo: FinaIndicatorRepository,
        cashflow_repo: CashFlowRepository,
        balance_repo: BalanceSheetRepository,
        tushare_service: TushareService
    ) -> None:
        self.company_resolver = company_resolver
        self.time_range_parser = time_range_parser
        self.data_completeness_checker = data_completeness_checker
        self.income_repo = income_repo
        self.indicator_repo = indicator_repo
        self.cashflow_repo = cashflow_repo
        self.balance_repo = balance_repo
        self.tushare_service = tushare_service

    def prepare(
        self,
        db: Session,
        time_range: TimeRange,
        required_parts: list[str],
        ts_code: str = None,
        company_name: str = None
    ) -> DataPreparationResult:
        already_backfill = False
        raw_financial_data = {}
        company_profile = self.company_resolver.resolve(
            db=db,
            company_name=company_name,
            ts_code=ts_code,
        )
        if required_parts is None:
            required_parts = settings.CORE_FINANCIAL_PARTS.copy()
        parsed_time_range = self.time_range_parser.parse(time_range)
        try:
            raw_financial_data = get_records_from_date_and_required_parts(
                db=db,
                ts_code=company_profile["ts_code"],
                start_date_obj=parsed_time_range.start_date_obj,
                end_date_obj=parsed_time_range.end_date_obj,
                required_parts=required_parts,
                list_of_repos=[self.income_repo, self.balance_repo, self.cashflow_repo, self.indicator_repo]
            )
        except ValueError as e:
            return DataPreparationResult(
                ts_code=company_profile["ts_code"],
                company_name=company_profile["name"],
                time_range=time_range,
                required_parts=required_parts,
                raw_financial_data=raw_financial_data,
                completeness_result=None,
                preparation_status="failed",
                message=str(e)
            )
        completeness_result = self.data_completeness_checker.check(
            requested_time_range=time_range,
            financial_data=raw_financial_data,
            required_parts=required_parts,
        )
        need_backfill = {}
        if completeness_result.needs_backfill and not already_backfill:
            already_backfill = True
            for item in completeness_result.part_details.values():
                if not item.is_complete:
                    need_backfill[item.part_name] = item.missing_periods

        backfill_data = {}
        print(need_backfill)
        for part_name, backfill_item in need_backfill.items():
            tushare_get_func = get_repo_or_func_from_part_name(part_name, tushare=self.tushare_service)
            for period in backfill_item:
                backfill_data[part_name] = backfill_data.get(part_name, []) + [tushare_get_func(ts_code=company_profile["ts_code"], period=period)]
            print(backfill_data)
            repo = get_repo_or_func_from_part_name(part_name, [self.income_repo, self.balance_repo, self.cashflow_repo, self.indicator_repo])
            repo.bulk_upsert(db=db, data=backfill_data[part_name])
        raw_financial_data = get_records_from_date_and_required_parts(
            db=db,
            ts_code=company_profile["ts_code"],
            start_date_obj=parsed_time_range.start_date_obj,
            end_date_obj=parsed_time_range.end_date_obj,
            required_parts=required_parts,
            list_of_repos=[self.income_repo, self.balance_repo, self.cashflow_repo, self.indicator_repo]
        )
        completeness_result = self.data_completeness_checker.check(
            requested_time_range=time_range,
            financial_data=raw_financial_data,
            required_parts=required_parts,
        )
        return DataPreparationResult(
            ts_code=company_profile["ts_code"],
            company_name=company_profile["name"],
            time_range=time_range,
            required_parts=required_parts,
            raw_financial_data=raw_financial_data,
            completeness_result=completeness_result,
            preparation_status="success",
            message=f"时间范围{parsed_time_range.start_date_obj} ~ {parsed_time_range.end_date_obj}数据准备完成，从TuShare获取数据{1 if already_backfill else 0}次。"
        )