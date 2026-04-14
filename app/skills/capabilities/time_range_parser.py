"""将TimeRange格式的日期转换为ParsedTimeRange"""

from datetime import date, datetime

from app.domain.models import TimeRange
from app.domain.models import ParsedTimeRange


class TimeRangeParser:
    def parse(self, time_range: TimeRange | None) -> ParsedTimeRange:
        start_date_str = f"{time_range.start_year}{time_range.start_month:02d}01"
        if time_range.end_year % 4 == 0 and time_range.end_year % 100 != 0 or time_range.end_year % 400 == 0:
            end_date_str = f"{time_range.end_year}{time_range.end_month:02d}29"
        elif time_range.end_month == 2:
            end_date_str = f"{time_range.end_year}{time_range.end_month:02d}28"
        elif time_range.end_month in [4, 6, 9, 11]:
            end_date_str = f"{time_range.end_year}{time_range.end_month:02d}30"
        else:
            end_date_str = f"{time_range.end_year}{time_range.end_month:02d}31"
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