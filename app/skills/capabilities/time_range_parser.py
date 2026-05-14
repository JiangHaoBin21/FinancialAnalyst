"""将TimeRange格式的日期转换为ParsedTimeRange"""

from datetime import date, datetime

from app.domain.models import ParsedTimeRange
from app.domain.models import TimeRange
from app.utils.date_utils import get_last_day_of_month, get_first_day_of_month


class TimeRangeParser:
    def parse(self, time_range: TimeRange | dict) -> ParsedTimeRange:
        start_year = _time_range_value(time_range, "start_year")
        start_month = _time_range_value(time_range, "start_month")
        end_year = _time_range_value(time_range, "end_year")
        end_month = _time_range_value(time_range, "end_month")

        start_year_month = f"{start_year}.{start_month:02d}"
        end_year_month = f"{end_year}.{end_month:02d}"
        start_date_str = get_first_day_of_month(start_year_month)
        end_date_str = get_last_day_of_month(end_year_month)
        return ParsedTimeRange(
            start_date_obj=datetime.strptime(start_date_str, "%Y%m%d").date(),
            end_date_obj=datetime.strptime(end_date_str, "%Y%m%d").date(),
            start_date_str=start_date_str,
            end_date_str=end_date_str
        )


def _time_range_value(time_range: TimeRange | dict, key: str) -> int:
    if isinstance(time_range, dict):
        return int(time_range[key])
    return int(getattr(time_range, key))


if __name__ == "__main__":
    parser = TimeRangeParser()
    time_range = TimeRange(start_year=2023, start_month=1, end_year=2025, end_month=9)
    parsed_time_range = parser.parse(time_range)
    print(parsed_time_range)
