from typing import Any
from app.core.config import settings
from app.domain.models import TimeRange, DataCompletenessResult, PartCompletenessDetail
from app.utils.date_utils import generate_quarter_ends


class DataCompletenessChecker:
    """检查数据是否完整，覆盖的季度是否足够"""

    def __init__(self) -> None:
        self.CORE_FINANCIAL_PARTS = settings.CORE_FINANCIAL_PARTS

    def check(
        self,
        requested_time_range: TimeRange | None,
        financial_data: dict[str, Any],
        required_parts: list[str] | None = None,
    ) -> DataCompletenessResult:
        tables = list(required_parts) if required_parts else self.CORE_FINANCIAL_PARTS.copy()

        requested_start_year_month = (
            f"{requested_time_range.start_year}.{requested_time_range.start_month:02d}"
        )
        requested_end_year_month = (
            f"{requested_time_range.end_year}.{requested_time_range.end_month:02d}"
        )
        expected_periods = generate_quarter_ends(
            requested_start_year_month,
            requested_end_year_month,
        )

        part_details = self.build_part_details(
            financial_data=financial_data,
            tables=tables,
            expected_periods=expected_periods,
        )

        missing_parts = [
            part_name
            for part_name, detail in part_details.items()
            if not detail.is_complete
        ]

        has_missing_data = bool(missing_parts)

        return DataCompletenessResult(
            needs_backfill=has_missing_data,
            missing_parts=missing_parts,
            expected_periods=expected_periods,
            part_details=part_details,
            has_missing_data=has_missing_data,
            completeness_reason=self.get_completeness_reason(part_details),
        )

    def build_part_details(
        self,
        financial_data: dict[str, Any],
        tables: list[str],
        expected_periods: list[str],
    ) -> dict[str, PartCompletenessDetail]:
        part_details: dict[str, PartCompletenessDetail] = {}

        for part_name in tables:
            records = financial_data.get(part_name) or []

            available_periods = []
            for record in records:
                end_date = str(record.end_date)
                if end_date not in available_periods:
                    available_periods.append(end_date)

            # 保持有序，便于调试和 summary 展示
            available_periods = sorted(available_periods)
            missing_periods = [
                period for period in expected_periods
                if period not in available_periods
            ]

            part_details[part_name] = PartCompletenessDetail(
                part_name=part_name,
                available_periods=available_periods,
                missing_periods=missing_periods,
                is_complete=(len(missing_periods) == 0),
                record_count=len(records),
            )

        return part_details

    def get_completeness_reason(
        self,
        part_details: dict[str, PartCompletenessDetail],
    ) -> str:
        incomplete_parts = [
            detail for detail in part_details.values()
            if not detail.is_complete
        ]

        if not incomplete_parts:
            return "DataAgent：数据完整性检查通过"

        empty_parts = [
            detail.part_name
            for detail in incomplete_parts
            if detail.record_count == 0
        ]

        partial_missing_parts = {
            detail.part_name: detail.missing_periods
            for detail in incomplete_parts
            if detail.record_count > 0 and detail.missing_periods
        }

        if empty_parts and not partial_missing_parts:
            return f"DataAgent：数据不完整，{empty_parts} 表为空"

        if partial_missing_parts and not empty_parts:
            return (
                f"DataAgent：数据不完整，缺少以下季度数据："
                f"{partial_missing_parts}"
            )

        return (
            f"DataAgent：数据不完整，{empty_parts} 表为空，且缺少以下季度数据："
            f"{partial_missing_parts}"
        )