"""检查即将交付的信息是否完整"""
from venv import CORE_VENV_DEPS

from app.domain.models import TimeRange
from app.domain.models import DataCompletenessResult


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
        missing_years = {key: [] for key in self.CORE_FINANCIAL_PARTS}




    def get_financial_data_range(self, financial_data: dict[str, Any]) -> dict[str, list]:
        """获取财务数据覆盖的区间"""
        covered_years = {key: [] for key in self.CORE_FINANCIAL_PARTS}
        for item in self.CORE_FINANCIAL_PARTS:
            records = financial_data.get(item)
            for record in records:
                if record.end_date.year not in covered_years[item]:
                    covered_years[item].append(record.end_date.year)

        return covered_years

