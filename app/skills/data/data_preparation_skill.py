"""原始数据数据准备skill"""

from __future__ import annotations

from typing import Any

from app.domain.models import TimeRange
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.helpers import get_repo_or_func_from_part_name, get_records_from_date_and_required_parts
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService
from app.skills.capabilities.time_range_parser import TimeRangeParser


class DataPreparationSkill:
    """
    数据准备 Skill

    职责：
    1. 解析时间范围
    2. 优先从本地库查询财务数据
    3. 支持回源 TuShare 并落库

    不负责：
    - 读写 WorkflowState
    - 控制 graph / node 流程
    - 财务分析
    - 报告生成
    """

    def __init__(
        self,
        time_range_parser: TimeRangeParser,
        income_repo: IncomeRepository,
        indicator_repo: FinaIndicatorRepository,
        cashflow_repo: CashFlowRepository,
        balance_repo: BalanceSheetRepository,
        tushare_service: TushareService,
        session_factory

    ) -> None:
        self.time_range_parser = time_range_parser
        self.income_repo = income_repo
        self.indicator_repo = indicator_repo
        self.cashflow_repo = cashflow_repo
        self.balance_repo = balance_repo
        self.tushare_service = tushare_service
        self.session_factory = session_factory

    def prepare(
        self,
        *,
        time_range: TimeRange,
        required_parts: list[str],
        company_profile: dict[str, Any],
        backfill: dict[str, list] = None
    ) -> list[dict]:
        """
        数据准备

        :param time_range: 时间范围
        :param required_parts: 需要的财务数据部分
        :param company_profile: 公司信息
        :param backfill: 需要回源的数据
        :return: 财务数据
        """
        with self.session_factory() as db:
            parsed_time_range = self.time_range_parser.parse(time_range)
            if backfill:
                backfill_data = []
                for part_name, need_backfill_item in backfill.items():
                    tushare_get_func = get_repo_or_func_from_part_name(part_name, tushare=self.tushare_service)
                    part_records = []
                    for period in need_backfill_item:
                        records = tushare_get_func(
                            ts_code=company_profile["ts_code"],
                            period=str(period).replace("-", ""),
                        )
                        part_records.extend(records)

                    repo = get_repo_or_func_from_part_name(part_name,
                                                           [self.income_repo, self.balance_repo, self.cashflow_repo,
                                                            self.indicator_repo])
                    repo.bulk_upsert(db=db, data=part_records)
                    backfill_data.extend(part_records)
                db.commit()
                return backfill_data
            else:
                raw_financial_data = get_records_from_date_and_required_parts(
                    db=db,
                    ts_code=company_profile["ts_code"],
                    start_date_obj=parsed_time_range.start_date_obj,
                    end_date_obj=parsed_time_range.end_date_obj,
                    required_parts=required_parts,
                    list_of_repos=[self.income_repo, self.balance_repo, self.cashflow_repo, self.indicator_repo]
                )
                return raw_financial_data
