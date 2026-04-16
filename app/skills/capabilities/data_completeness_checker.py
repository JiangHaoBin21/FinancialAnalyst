"""检查即将交付的信息是否完整"""
from venv import CORE_VENV_DEPS

from app.domain.models import TimeRange
from app.domain.models import DataCompletenessResult
from typing import Any

from app.repositories.helpers import generate_quarter_ends


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
        required_parts: str | None = None,
    ) -> DataCompletenessResult:
        missing_part = []
        tables = self.CORE_FINANCIAL_PARTS.copy()
        for item in self.CORE_FINANCIAL_PARTS:
            records = financial_data.get(item)
            if not records:
                missing_part.append(item)
                tables.remove(item)

        requested_start_year_month = f"{requested_time_range.start_year}.{requested_time_range.start_month:02d}"
        requested_end_year_month = f"{requested_time_range.end_year}.{requested_time_range.end_month:02d}"
        excepted_periods = generate_quarter_ends(requested_start_year_month, requested_end_year_month)
        print("tables:", tables)
        available_periods_by_part = self.get_financial_data_range(financial_data, tables)
        missing_periods_by_part = self.check_missing_periods(available_periods_by_part, excepted_periods)

        return DataCompletenessResult(
            needs_backfill=bool(missing_part or missing_periods_by_part),
            missing_parts=missing_part,
            available_periods_by_part=available_periods_by_part,
            expected_periods=excepted_periods,
            missing_periods_by_part=missing_periods_by_part,
            has_missing_data=bool(missing_part or missing_periods_by_part),
            completeness_reason=self.get_completeness_reason(missing_part, missing_periods_by_part)
        )


    def get_financial_data_range(self, financial_data: dict[str, Any], tables: list[str]) -> dict[str, list]:
        """获取财务数据覆盖的区间"""
        covered_periods = {key: [] for key in tables}
        for item in tables:
            records = financial_data.get(item)
            for record in records:
                if record.end_date not in covered_periods[item]:
                    covered_periods[item].append(str(record.end_date))

        return covered_periods

    def check_missing_periods(self, available_periods_by_part: dict[str, Any], excepted_periods: list[str]) -> dict[str, Any]:
        """检查缺失的季报"""
        missing_period = {}
        for key, value in available_periods_by_part.items():
            missing_value = list(set(excepted_periods) - set(value))
            if missing_value:
                missing_period[key] = missing_value
        return missing_period

    def get_completeness_reason(self, missing_part, missing_periods_by_part):
        if not (missing_part or missing_periods_by_part):
            return "DataAgent：数据完整性检查通过"
        elif missing_part and not missing_periods_by_part:
            return f"DataAgent：数据不完整，{missing_part} 表为空"
        elif missing_periods_by_part and not missing_part:
            return f"DataAgent：数据不完整，缺少 {missing_periods_by_part.keys()} 表中 {missing_periods_by_part.values()} 季度数据"
        else:
            return f"DataAgent：数据不完整，{missing_part} 表为空，且缺少 {missing_periods_by_part.keys()} 表中 {missing_periods_by_part.values()} 季度数据"
