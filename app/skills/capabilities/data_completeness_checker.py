from typing import Any
from app.core.config import settings
from app.domain.models import TimeRange, DataCompletenessResult, PartCompletenessDetail
from app.utils.date_utils import generate_quarter_ends


class DataCompletenessChecker:
    """检查数据是否完整，覆盖的季度是否足够"""

    def check(
        self,
        requested_time_range: TimeRange | dict | None,
        financial_data: dict[str, Any],
        required_parts: list[str] | None = None,
    ) -> DataCompletenessResult:
        if requested_time_range is None:
            raise ValueError("requested_time_range is required")

        tables = list(required_parts or financial_data.keys() or settings.CORE_FINANCIAL_PARTS)

        start_year = self._time_range_value(requested_time_range, "start_year")
        start_month = self._time_range_value(requested_time_range, "start_month")
        end_year = self._time_range_value(requested_time_range, "end_year")
        end_month = self._time_range_value(requested_time_range, "end_month")

        requested_start_year_month = f"{start_year}.{start_month:02d}"
        requested_end_year_month = f"{end_year}.{end_month:02d}"
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
            detail.part_name
            for detail in part_details
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
    ) -> list[PartCompletenessDetail]:

        part_details = []
        for part_name in tables:
            records = financial_data.get(part_name) or []

            available_periods = []
            for record in self._iter_records(records):
                end_date = self._extract_end_date(record)
                if end_date is None:
                    continue
                if end_date not in available_periods:
                    available_periods.append(end_date)

            # 保持有序，便于调试和 summary 展示
            available_periods = sorted(available_periods)
            missing_periods = [
                period for period in expected_periods
                if period not in available_periods
            ]

            part_details.append(
                PartCompletenessDetail(
                    part_name=part_name,
                    available_periods=available_periods,
                    missing_periods=missing_periods,
                    is_complete=(len(missing_periods) == 0),
                    record_count=len(records),
                )
            )

        return part_details

    @classmethod
    def _iter_records(cls, records: Any):
        if isinstance(records, list):
            for record in records:
                if isinstance(record, list):
                    yield from cls._iter_records(record)
                else:
                    yield record
            return
        yield records

    @staticmethod
    def _extract_end_date(record: Any) -> str | None:
        if isinstance(record, dict):
            end_date = record.get("end_date")
        else:
            end_date = getattr(record, "end_date", None)

        if end_date is None:
            return None
        if hasattr(end_date, "isoformat"):
            return end_date.isoformat()

        text = str(end_date).strip()
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:]}"
        return text

    @staticmethod
    def _time_range_value(time_range: TimeRange | dict, key: str) -> int:
        if isinstance(time_range, dict):
            return int(time_range[key])
        return int(getattr(time_range, key))

    def get_completeness_reason(
        self,
        part_details: list[PartCompletenessDetail],
    ) -> str:
        incomplete_parts = [
            detail for detail in part_details
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
