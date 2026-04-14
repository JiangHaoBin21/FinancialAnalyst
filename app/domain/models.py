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
class DataCompletenessResult:
    """数据完整性检查结果"""
    needs_backfill: bool
    missing_parts: list[str] = field(default_factory=list)
    years_covered: list[int] = field(default_factory=list)
    expected_years: list[int] = field(default_factory=list)
    missing_years: list[int] = field(default_factory=list)
    has_missing_data: bool = False
    completeness_reason: str = ""