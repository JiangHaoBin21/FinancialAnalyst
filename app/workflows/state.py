"""LangGraph 原生工作流状态定义。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from app.domain.models import TimeRange


def append_list(left: Optional[list[Any]], right: Optional[list[Any]]) -> list[Any]:
    """用于并行 LangGraph 节点写入列表字段的归并器。"""
    return list(left or []) + list(right or [])


class TaskType(str, Enum):
    FINANCIAL_ANALYSIS = "financial_analysis"
    UNKNOWN = "unknown"


class WorkflowStep(str, Enum):
    SUPERVISOR = "supervisor"
    AWAIT_USER_INPUT = "await_user_input"
    DATA = "data"
    ANALYSIS = "analysis"
    REPORT = "report"
    REFLECTION = "reflection"
    FINISHED = "finished"
    ERROR = "error"


class OutputMode(str, Enum):
    REPORT = "report"
    SUMMARY = "summary"


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    INIT = "init"
    NEEDS_USER_INPUT = "needs_user_input"
    READY_FOR_EXECUTION = "ready_for_execution"
    DATA_PLANNED = "data_planned"
    DATA_READY = "data_ready"
    ANALYSIS_READY = "analysis_ready"
    REPORT_READY = "report_ready"
    REFLECTION_DONE = "reflection_done"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class PlanStep:
    """由 Supervisor 规划器生成的高层 Agent 步骤。"""

    step_id: int
    agent: str
    action: str
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING


@dataclass
class ExecutionRecord:
    """用于观测图节点和 Agent 执行过程的记录。"""

    step: str
    agent: str
    success: bool
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataPartResult:
    """并行数据抓取节点产出的单个数据分片结果。"""

    part_name: str
    payload: Any
    success: bool = True
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowState(TypedDict, total=False):
    # 用户输入
    user_query: str

    # Supervisor 与规划层
    task_type: TaskType
    company_name: Optional[str]
    ts_code: Optional[str]
    time_range: Optional[TimeRange]
    analysis_focus: Optional[str]
    output_mode: OutputMode
    planner_message: Optional[str]
    raw_planner_response: Optional[str]
    needs_user_input: bool
    missing_fields: list[str]
    task_plan: list[PlanStep]
    current_step_index: int
    completed_step_ids: list[int]
    company_profile: dict[str, Any]

    # 数据规划与并行扇出层
    required_data_parts: list[str]
    data_part_results: Annotated[list[DataPartResult], append_list]
    data_fetch_errors: Annotated[list[str], append_list]

    # 数据合并结果
    financial_data: dict[str, Any]
    data_summary: dict[str, Any]

    # 数据检查完整性
    data_completeness_check_result: dict[str, Any]

    # 是否需要回源补充（数据检查完整性后）
    need_backfill: dict[str, list[str]]
    already_backfill: int

    # 分析结果
    analysis_result: dict[str, Any]
    analysis_summary: Optional[str]

    # 报告结果
    report_draft: Optional[str]
    report_sections: dict[str, Any]
    final_report: Optional[str]

    # 反思结果
    reflection_result: dict[str, Any]
    needs_revision: bool
    replan_required: bool

    # 流程控制
    current_stage: WorkflowStep
    next_step: Optional[WorkflowStep]
    status: WorkflowStatus
    is_finished: bool
    has_error: bool
    error_message: Optional[str]
    assistant_message: Optional[str]

    # 可观测性
    execution_history: Annotated[list[ExecutionRecord], append_list]

    # 最终输出
    final_response: Optional[str]


# 数据抓取分片名称，需与 DataAgent 规划结果和 LangGraph 路由保持一致。
DATA_PART_COMPANY_PROFILE = "company_profile"
DATA_PART_INCOME = "income_statements"
DATA_PART_BALANCE = "balance_sheets"
DATA_PART_CASHFLOW = "cashflow_statements"
DATA_PART_INDICATORS = "financial_indicators"

CORE_DATA_PARTS = [
    DATA_PART_COMPANY_PROFILE,
    DATA_PART_INCOME,
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INDICATORS,
]


def create_initial_state(user_query: str) -> WorkflowState:
    """创建完整初始状态，确保图节点可以安全读取默认值。"""
    return {
        "user_query": user_query,
        "task_type": TaskType.UNKNOWN,
        "company_name": None,
        "ts_code": None,
        "time_range": None,
        "analysis_focus": None,
        "output_mode": OutputMode.REPORT,
        "planner_message": None,
        "raw_planner_response": None,
        "needs_user_input": False,
        "missing_fields": [],
        "task_plan": [],
        "current_step_index": 0,
        "completed_step_ids": [],
        "required_data_parts": [],
        "data_part_results": [],
        "data_fetch_errors": [],
        "company_profile": {},
        "financial_data": {},
        "data_summary": {},
        "data_completeness_check_result": {},
        "need_backfill": {},
        "already_backfill": 0,
        "analysis_result": {},
        "analysis_summary": None,
        "report_draft": None,
        "report_sections": {},
        "final_report": None,
        "reflection_result": {},
        "needs_revision": False,
        "replan_required": False,
        "current_stage": WorkflowStep.SUPERVISOR,
        "next_step": WorkflowStep.SUPERVISOR,
        "status": WorkflowStatus.INIT,
        "is_finished": False,
        "has_error": False,
        "error_message": None,
        "assistant_message": None,
        "execution_history": [],
        "final_response": None,
    }


def execution_record(
    step: str,
    agent: str,
    success: bool,
    message: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> ExecutionRecord:
    """创建统一格式的执行记录。"""
    return ExecutionRecord(
        step=step,
        agent=agent,
        success=success,
        message=message,
        metadata=metadata or {},
    )


def get_current_plan_step(state: WorkflowState) -> Optional[PlanStep]:
    """根据 current_step_index 读取当前计划步骤。"""
    index = state.get("current_step_index", 0)
    task_plan = state.get("task_plan", [])
    if index < 0 or index >= len(task_plan):
        return None
    return task_plan[index]


def update_current_plan_step_status(
    state: WorkflowState,
    status: PlanStepStatus,
) -> list[PlanStep]:
    """返回更新了当前步骤状态的新计划列表。"""
    # 复制计划步骤，避免原地修改传入状态。
    task_plan = [
        PlanStep(
            step_id=step.step_id,
            agent=step.agent,
            action=step.action,
            description=step.description,
            status=step.status,
        )
        for step in state.get("task_plan", [])
    ]
    index = state.get("current_step_index", 0)
    if 0 <= index < len(task_plan):
        task_plan[index].status = status
    return task_plan


def complete_current_plan_step(state: WorkflowState) -> dict[str, Any]:
    """标记当前计划步骤完成，并推进到下一步。"""
    task_plan = update_current_plan_step_status(state, PlanStepStatus.DONE)
    step = get_current_plan_step(state)
    completed_step_ids = list(state.get("completed_step_ids", []))
    if step is not None and step.step_id not in completed_step_ids:
        completed_step_ids.append(step.step_id)

    current_step_index = state.get("current_step_index", 0) + 1
    # 计划索引推进后，重新计算下一类工作流节点。
    next_step = next_workflow_step(task_plan, current_step_index)
    return {
        "task_plan": task_plan,
        "completed_step_ids": completed_step_ids,
        "current_step_index": current_step_index,
        "next_step": next_step,
    }


def fail_current_plan_step(state: WorkflowState) -> dict[str, Any]:
    """标记当前计划步骤失败。"""
    return {"task_plan": update_current_plan_step_status(state, PlanStepStatus.FAILED)}


def next_workflow_step(
    task_plan: list[PlanStep],
    current_step_index: int,
) -> WorkflowStep:
    """根据计划中的 Agent 名称计算下一类工作流步骤。"""
    if current_step_index < 0 or current_step_index >= len(task_plan):
        return WorkflowStep.FINISHED

    # 计划步骤中的 Agent 名称决定下一类工作流节点。
    agent_to_workflow_step = {
        "DataAgent": WorkflowStep.DATA,
        "AnalysisAgent": WorkflowStep.ANALYSIS,
        "ReportAgent": WorkflowStep.REPORT,
        "ReflectionAgent": WorkflowStep.REFLECTION,
    }
    return agent_to_workflow_step.get(task_plan[current_step_index].agent, WorkflowStep.ERROR)


def is_current_plan_agent(state: WorkflowState, expected_agent: str) -> bool:
    """判断当前计划步骤是否应该由指定 Agent 执行。"""
    step = get_current_plan_step(state)
    return step is not None and step.agent == expected_agent


def error_update(message: str) -> dict[str, Any]:
    """构造进入错误态所需的统一状态更新。"""
    return {
        "has_error": True,
        "error_message": message,
        "status": WorkflowStatus.ERROR,
        "current_stage": WorkflowStep.ERROR,
        "next_step": WorkflowStep.ERROR,
        "is_finished": False,
        "assistant_message": message,
    }


def normalize_for_json(obj: Any) -> Any:
    """递归转换 dataclass 和枚举，生成 JSON 友好的对象。"""
    if is_dataclass(obj):
        return normalize_for_json(asdict(obj))
    if isinstance(obj, dict):
        return {k: normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_for_json(v) for v in obj]
    if hasattr(obj, "value"):
        return obj.value
    return obj
