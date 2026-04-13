"""原始数据数据准备skill"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.domain.models import TimeRange
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.capabilities.financial_data_query import FinancialDataQuery
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.capabilities.financial_data_fetcher import FinancialDataFetcher
from app.skills.capabilities.financial_data_persistence import FinancialDataPersistence
from app.skills.capabilities.data_summary_builder import DataSummaryBuilder


@dataclass
class DataPreparationResult:
    company_profile: dict[str, Any]
    financial_data: dict[str, Any]
    data_summary: dict[str, Any]
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


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
        financial_data_query: FinancialDataQuery,
        data_completeness_checker: DataCompletenessChecker,
        financial_data_fetcher: FinancialDataFetcher,
        financial_data_persistence: FinancialDataPersistence,
        data_summary_builder: DataSummaryBuilder,
    ) -> None:
        self.company_resolver = company_resolver
        self.time_range_parser = time_range_parser
        self.financial_data_query = financial_data_query
        self.data_completeness_checker = data_completeness_checker
        self.financial_data_fetcher = financial_data_fetcher
        self.financial_data_persistence = financial_data_persistence
        self.data_summary_builder = data_summary_builder

    def execute(
        self,
        company_name: Optional[str],
        ts_code: Optional[str],
        time_range: Optional[TimeRange],
        analysis_focus: Optional[str] = None,
    ) -> DataPreparationResult:
        if not company_name and not ts_code:
            raise ValueError("DataPreparationSkill 缺少 company_name 或 ts_code")

        # 1) 公司解析：优先本地，必要时回源并补库
        company_profile, company_source = self.company_resolver.resolve(
            company_name=company_name,
            ts_code=ts_code,
        )

        # 2) 时间范围解析
        parsed_range = self.time_range_parser.parse(time_range)

        # 3) 本地查询
        local_financial_data = self.financial_data_query.query(
            ts_code=company_profile["ts_code"],
            start_date=parsed_range.start_date_obj,
            end_date=parsed_range.end_date_obj,
        )

        # 4) 完整性检查
        completeness = self.data_completeness_checker.check(
            requested_time_range=time_range,
            financial_data=local_financial_data,
        )

        fetched_financial_data = {
            "income_statements": [],
            "balance_sheets": [],
            "cashflow_statements": [],
            "financial_indicators": [],
        }
        fetch_sources = {
            "income_statements": "db",
            "balance_sheets": "db",
            "cashflow_statements": "db",
            "financial_indicators": "db",
        }

        # 5) 不足时回源并落库
        if completeness.needs_backfill:
            fetched_financial_data = self.financial_data_fetcher.fetch(
                ts_code=company_profile["ts_code"],
                start_date=parsed_range.start_date_str,
                end_date=parsed_range.end_date_str,
                analysis_focus=analysis_focus,
                missing_parts=completeness.missing_parts,
            )

            self.financial_data_persistence.persist(
                company_profile=company_profile,
                financial_data=fetched_financial_data,
            )

            # 重新查询，保证下游统一消费“库中标准数据”
            final_financial_data = self.financial_data_query.query(
                ts_code=company_profile["ts_code"],
                start_date=parsed_range.start_date_obj,
                end_date=parsed_range.end_date_obj,
            )

            for part in completeness.missing_parts:
                fetch_sources[part] = "tushare+persisted"
        else:
            final_financial_data = local_financial_data

        # 6) 构建摘要
        data_summary = self.data_summary_builder.build(
            company_profile=company_profile,
            financial_data=final_financial_data,
            requested_time_range=time_range,
            normalized_start_date=parsed_range.start_date_str,
            normalized_end_date=parsed_range.end_date_str,
            company_source=company_source,
            financial_data_sources=fetch_sources,
            completeness=completeness,
        )

        message = f"已完成 {company_profile['company_name']} 的财务数据准备。"

        metadata = {
            "company_name": company_profile.get("company_name"),
            "ts_code": company_profile.get("ts_code"),
            "years_covered": data_summary.get("years_covered", []),
            "record_counts": data_summary.get("record_counts", {}),
            "source_strategy": data_summary.get("source_strategy"),
        }

        return DataPreparationResult(
            company_profile=company_profile,
            financial_data=final_financial_data,
            data_summary=data_summary,
            message=message,
            metadata=metadata,
        )