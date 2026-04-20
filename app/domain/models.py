"""定义所有使用的数据结构"""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import date

@dataclass
class PlanningStep:
    """单个规划步骤。"""

    step_id: int
    agent: str
    action: str
    description: str


@dataclass
class TimeRange:
    """时间范围。"""

    start_year: int
    start_month: int
    end_year: int
    end_month: int


@dataclass
class PlanningResult:
    """
    规划结果（系统内部标准对象）。

    注意：
    - 这是 Python 内部使用的真实对象
    - 不是直接给 LLM 的 schema
    """

    task_type: str
    company_name: Optional[str] = None
    ts_code: Optional[str] = None
    time_range: Optional[TimeRange] = None
    analysis_focus: Optional[str] = None
    output_mode: str = "report"  # report | summary
    planner_message: str = ""
    task_plan: list[PlanningStep] = field(default_factory=list)
    needs_user_input: bool = False
    missing_fields: list[str] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class ParsedTimeRange:
    """
    解析后的时间范围：YYYYMMDD风格
    obj供repo查询使用，
    字符串供TuShare接口使用。
    """
    start_date_obj: Optional[date]
    end_date_obj: Optional[date]
    start_date_str: Optional[str]
    end_date_str: Optional[str]


@dataclass
class PartCompletenessDetail:
    """单个数据表（part）的完整性详情"""
    part_name: str
    available_periods: list[str]
    missing_periods: list[str]
    is_complete: bool
    record_count: int = 0


@dataclass
class DataCompletenessResult:
    """数据完整性检查结果"""
    needs_backfill: bool
    missing_parts: list[str]

    expected_periods: list[str]
    part_details: dict[str, PartCompletenessDetail]

    has_missing_data: bool
    completeness_reason: str


@dataclass
class DataPreparationResult:
    ts_code: str
    company_name: str
    time_range: TimeRange
    required_parts: list[str]

    raw_financial_data: dict[str, list[dict]]
    completeness_result: DataCompletenessResult | None

    preparation_status: str
    message: str = ""


@dataclass
class DataSummary:
    """数据摘要，供AnalysisAgent使用"""
    ts_code: str
    company_name: str

    normalized_start_date: Optional[str]
    normalized_end_date: Optional[str]

    company_source: str
    financial_data_sources: dict[str, str]

    record_counts: dict[str, int]
    latest_end_date: Optional[str]