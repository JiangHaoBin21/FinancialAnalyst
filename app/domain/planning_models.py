"""planning_skills数据结构"""

from dataclasses import dataclass, field
from typing import Any, Optional

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