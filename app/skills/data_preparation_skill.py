"""原始数据数据准备skill"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domain.models import TimeRange, DataPreparationResult
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.helpers import get_repo_from_part_name
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
    ) -> None:
        self.company_resolver = company_resolver
        self.time_range_parser = time_range_parser
        self.data_completeness_checker = data_completeness_checker
        self.income_repo = income_repo
        self.indicator_repo = indicator_repo
        self.cashflow_repo = cashflow_repo
        self.balance_repo = balance_repo

    def prepare(
        self,
        db: Session,
        ts_code: str,
        company_name: str,
        time_range: TimeRange,
        required_parts: list[str],
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
        for part_name in required_parts:
            if part_name not in settings.CORE_FINANCIAL_PARTS:
                raise ValueError(f"非法的财务数据表名: {part_name}")
            repo = get_repo_from_part_name(part_name, [self.income_repo, self.balance_repo, self.cashflow_repo, self.indicator_repo])
            parsed_time_range = self.time_range_parser.parse(time_range)
            raw_financial_data[part_name] = (
                repo.list_by_ts_code_and_date_range(
                    db=db,
                    ts_code=company_profile["ts_code"],
                    start_date=parsed_time_range.start_date_obj,
                    end_date=parsed_time_range.end_date_obj
                ))
        completeness_result = self.data_completeness_checker.check(
            requested_time_range=time_range,
            financial_data=raw_financial_data,
            required_parts=required_parts,
        )
        need_backfill = {}
        if completeness_result.needs_backfill and not already_backfill:
            for item in completeness_result.part_details.values():
                if not item.is_complete:

