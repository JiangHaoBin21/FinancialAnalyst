"""检查即将交付的信息是否完整"""
from venv import CORE_VENV_DEPS

from app.domain.models import TimeRange
from app.domain.models import DataCompletenessResult
from typing import Any


class DataCompletenessChecker:
    """检查数据是否完整，覆盖的年限是否足够"""
    CORE_FINANCIAL_PARTS = [
        "income_statements",
        "balance_sheets",
        "cashflow_statements",
        "financial_indicators",
    ]

    def check(
        self,
        requested_time_range: TimeRange | None,
        financial_data: dict[str, Any],
        analysis_focus: str | None = None,
    ) -> DataCompletenessResult:
        missing_part = []
        for item in self.CORE_FINANCIAL_PARTS:
            records = financial_data.get(item)
            if not records:
                missing_part.append(item)

        covered_years = self.get_financial_data_range(financial_data)
        missing_years = self.check_missing_years(covered_years, requested_time_range)

        return DataCompletenessResult(
            needs_backfill=bool(missing_part or missing_years),
            missing_parts=missing_part,
            years_covered=covered_years,
            expected_years=list(range(requested_time_range.start_year, requested_time_range.end_year + 1)),
            missing_years=missing_years,
            has_missing_data=bool(missing_part or missing_years),
            completeness_reason=self.get_completeness_reason(missing_part, missing_years)
        )


    def get_financial_data_range(self, financial_data: dict[str, Any]) -> dict[str, list]:
        """获取财务数据覆盖的区间"""
        covered_years = {key: [] for key in self.CORE_FINANCIAL_PARTS}
        for item in self.CORE_FINANCIAL_PARTS:
            records = financial_data.get(item)
            for record in records:
                if record.end_date.year not in covered_years[item]:
                    covered_years[item].append(record.end_date.year)

        return covered_years

    def check_missing_years(self, covered_years: dict[str, Any], requested_time_range: TimeRange) -> dict[str, Any]:
        """检查缺失的年份"""
        missing_years = {}
        requested_years = range(requested_time_range.start_year, requested_time_range.end_year + 1)
        for item in self.CORE_FINANCIAL_PARTS:
            records = covered_years.get(item)
            missing_years[item] = [year for year in requested_years if year not in records]
        return missing_years

    def get_completeness_reason(self, missing_part, missing_years):
        if not (missing_part and missing_years):
            return "DataAgent：数据完整性检查通过"
        elif missing_part and not missing_years:
            return f"DataAgent：数据不完整，缺少 {missing_part} 表中数据"
        elif missing_years and not missing_part:
            return f"DataAgent：数据不完整，缺少 {missing_years.keys()} 表中 {missing_years.values()} 年数据"
        else:
            return f"DataAgent：数据不完整，{missing_part} 表为空，且缺少 {missing_years.keys()} 表中 {missing_years.values()} 年数据"