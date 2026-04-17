"""将TimeRange格式的日期转换为ParsedTimeRange"""

from datetime import date, datetime

from app.domain.models import TimeRange
from app.domain.models import ParsedTimeRange
from app.utils.date_utils import get_last_day_of_month, get_first_day_of_month


class TimeRangeParser:
    def parse(self, time_range: TimeRange | None) -> ParsedTimeRange:
        start_year_month = f"{time_range.start_year}.{time_range.start_month:02d}"
        end_year_month = f"{time_range.end_year}.{time_range.end_month:02d}"
        start_date_str = get_first_day_of_month(start_year_month)
        end_date_str = get_last_day_of_month(end_year_month)
        return ParsedTimeRange(
            start_date_obj=datetime.strptime(start_date_str, "%Y%m%d").date(),
            end_date_obj=datetime.strptime(end_date_str, "%Y%m%d").date(),
            start_date_str=start_date_str,
            end_date_str=end_date_str
        )

if __name__ == "__main__":
    parser = TimeRangeParser()
    time_range = TimeRange(start_year=2023, start_month=1, end_year=2025, end_month=9)
    parsed_time_range = parser.parse(time_range)
    print(parsed_time_range)