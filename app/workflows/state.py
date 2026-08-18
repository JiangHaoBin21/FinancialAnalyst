"""LangGraph 原生工作流状态定义。"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from math import isfinite
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


PlanStep = dict[str, Any]
ExecutionRecord = dict[str, Any]
DataPartResult = dict[str, Any]
TimeRangeState = dict[str, int]


class WorkflowState(TypedDict, total=False):
    # 用户输入
    user_query: str

    # Supervisor 与规划层
    task_type: str
    company_name: Optional[str]
    ts_code: Optional[str]
    time_range: Optional[TimeRangeState]
    analysis_focus: Optional[str]
    output_mode: str
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
    financial_data: dict[str, list]
    data_summary: Optional[str]

    # 数据检查完整性
    data_completeness_check_result: dict[str, Any]

    # 是否需要回源补充（数据检查完整性后）
    need_backfill: dict[str, list[str]]
    already_backfill: int

    # 分析结果
    analysis_result: dict[str, Any]
    analysis_summary: Optional[str]

    # 报告结果
    report_result: dict
    final_report: Optional[str]

    # 反思结果
    reflection_result: dict[str, Any]
    needs_revision: bool
    replan_required: bool

    # 流程控制
    current_stage: str
    next_step: Optional[str]
    status: str
    is_finished: bool
    has_error: bool
    error_message: Optional[str]
    # agent间通讯的消息
    trans_message: Optional[str]
    # 给人看的消息
    assistant_message: Optional[str]
    # 上一次完成阶段（用于supervisor审查和重定向）
    last_completed_stage: str | None
    # 上一阶段输出
    stage_outputs: dict | None
    # 每个大阶段最大进入次数
    max_stage_attempts: int
    # 记录每个大阶段已经执行的次数
    stage_attempt_counts: dict[str, int]

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
        "task_type": TaskType.UNKNOWN.value,
        "company_name": None,
        "ts_code": None,
        "time_range": None,
        "analysis_focus": None,
        "output_mode": OutputMode.REPORT.value,
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
        "data_summary": None,
        "data_completeness_check_result": {},
        "need_backfill": {},
        "already_backfill": 0,
        "analysis_result": {},
        "analysis_summary": None,
        "report_result": {},
        "final_report": None,
        "reflection_result": {},
        "needs_revision": False,
        "replan_required": False,
        "current_stage": WorkflowStep.SUPERVISOR.value,
        "next_step": WorkflowStep.SUPERVISOR.value,
        "status": WorkflowStatus.INIT.value,
        "is_finished": False,
        "has_error": False,
        "error_message": None,
        "assistant_message": None,
        "trans_message": None,
        "last_completed_stage": None,
        "stage_outputs": None,
        "max_stage_attempts": 3,
        "stage_attempt_counts": {},
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
    return {
        "step": state_value(step),
        "agent": str(agent),
        "success": bool(success),
        "message": str(message or ""),
        "metadata": make_json_safe(metadata or {}),
    }


def data_part_result(
    part_name: str,
    payload: Any,
    success: bool = True,
    message: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> DataPartResult:
    """创建 JSON-safe 的单个数据分片结果。"""
    return {
        "part_name": str(part_name),
        "payload": make_json_safe(payload),
        "success": bool(success),
        "message": str(message or ""),
        "metadata": make_json_safe(metadata or {}),
    }


def plan_step(
    *,
    step_id: int,
    agent: str,
    action: str,
    description: str,
    status: PlanStepStatus | str = PlanStepStatus.PENDING,
) -> PlanStep:
    """创建 JSON-safe 的计划步骤。"""
    return {
        "step_id": int(step_id),
        "agent": str(agent),
        "action": str(action),
        "description": str(description),
        "status": state_value(status),
    }


def get_current_plan_step(state: WorkflowState) -> Optional[PlanStep]:
    """根据 current_step_index 读取当前计划步骤。"""
    index = state.get("current_step_index", 0)
    task_plan = state.get("task_plan", [])
    if index < 0 or index >= len(task_plan):
        return None
    return task_plan[index]


def update_current_plan_step_status(
    state: WorkflowState,
    status: PlanStepStatus | str,
) -> list[PlanStep]:
    """返回更新了当前步骤状态的新计划列表。"""
    # 复制计划步骤，避免原地修改传入状态。
    task_plan = [
        plan_step(
            step_id=step.get("step_id", 0),
            agent=step.get("agent", ""),
            action=step.get("action", ""),
            description=step.get("description", ""),
            status=step.get("status", PlanStepStatus.PENDING.value),
        )
        for step in state.get("task_plan", [])
    ]
    index = state.get("current_step_index", 0)
    if 0 <= index < len(task_plan):
        task_plan[index]["status"] = state_value(status)
    return task_plan


def complete_current_plan_step(state: WorkflowState) -> dict[str, Any]:
    """标记当前计划步骤完成，并推进到下一步。"""
    task_plan = update_current_plan_step_status(state, PlanStepStatus.DONE)
    step = get_current_plan_step(state)
    completed_step_ids = list(state.get("completed_step_ids", []))
    step_id = step.get("step_id") if step else None
    if step_id is not None and step_id not in completed_step_ids:
        completed_step_ids.append(step_id)

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
) -> str:
    """根据计划中的 Agent 名称计算下一类工作流步骤。"""
    if current_step_index < 0 or current_step_index >= len(task_plan):
        return WorkflowStep.FINISHED.value

    # 计划步骤中的 Agent 名称决定下一类工作流节点。
    agent_to_workflow_step = {
        "DataAgent": WorkflowStep.DATA.value,
        "AnalysisAgent": WorkflowStep.ANALYSIS.value,
        "ReportAgent": WorkflowStep.REPORT.value,
        "ReflectionAgent": WorkflowStep.REFLECTION.value,
    }
    return agent_to_workflow_step.get(
        str(task_plan[current_step_index].get("agent", "")),
        WorkflowStep.ERROR.value,
    )


def is_current_plan_agent(state: WorkflowState, expected_agent: str) -> bool:
    """判断当前计划步骤是否应该由指定 Agent 执行。"""
    step = get_current_plan_step(state)
    return step is not None and step.get("agent") == expected_agent


def error_update(message: str) -> dict[str, Any]:
    """构造进入错误态所需的统一状态更新。"""
    return {
        "has_error": True,
        "error_message": message,
        "status": WorkflowStatus.ERROR.value,
        "current_stage": WorkflowStep.ERROR.value,
        "next_step": WorkflowStep.ERROR.value,
        "is_finished": False,
        "assistant_message": message,
    }


def resolve_final_report(state: WorkflowState) -> Optional[str]:
    """解析当前状态中应交付给用户的最终 Markdown 报告。

    ``final_report`` 是新的显式交付字段。兼容旧 checkpoint 时，如果
    Reflection 已经给出轻量修订稿但尚未提升到该字段，也会读取嵌套在
    ``reflection_result.final_report_markdown`` 中的完整报告。
    """
    reflection_result = state.get("reflection_result")
    if isinstance(reflection_result, dict):
        decision = reflection_result.get("decision")
        if decision == "pass_with_minor_revision":
            # 轻量修订必须交付修订后的完整正文；字段缺失时不能静默
            # 回退到 Reflection 已判定需要修改的原稿。
            return (
                _non_empty_string(state.get("final_report"))
                or _non_empty_string(
                    reflection_result.get("final_report_markdown")
                )
            )

        if decision == "pass":
            final_report = _non_empty_string(state.get("final_report"))
            if final_report is not None:
                return final_report

            report_result = state.get("report_result")
            if isinstance(report_result, dict):
                return _non_empty_string(report_result.get("markdown_report"))

            return None

        if decision in {
            "needs_report_regeneration",
            "needs_analysis_revision",
            "needs_more_data",
            "failed",
        }:
            # Reflection 尚未批准交付，旧报告或旧 final_response 都不能
            # 被当成最终报告返回。
            return None

    final_report = _non_empty_string(state.get("final_report"))
    if final_report is not None:
        return final_report

    report_result = state.get("report_result")
    if isinstance(report_result, dict):
        report_draft = _non_empty_string(report_result.get("markdown_report"))
        if report_draft is not None:
            return report_draft

    return _non_empty_string(state.get("final_response"))


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def normalize_for_json(obj: Any) -> Any:
    """递归转换 dataclass 和枚举，生成 JSON 友好的对象。"""
    return make_json_safe(obj)


def make_json_safe(obj: Any) -> Any:
    """把常见 Python 对象转换为 JSON-native 值。"""
    if isinstance(obj, Enum):
        return obj.value
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if isfinite(obj) else None
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj):
        return make_json_safe(asdict(obj))
    if isinstance(obj, dict):
        return {str(make_json_safe(k)): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]
    return str(obj)


def state_value(value: Any) -> Any:
    """返回适合写入 state 的标量值。"""
    return value.value if isinstance(value, Enum) else value


def time_range_to_state(value: TimeRange | dict[str, Any] | None) -> TimeRangeState | None:
    """把 TimeRange 转为可写入 state 的 JSON-safe dict。"""
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            "start_year": int(value["start_year"]),
            "start_month": int(value["start_month"]),
            "end_year": int(value["end_year"]),
            "end_month": int(value["end_month"]),
        }
    return {
        "start_year": int(value.start_year),
        "start_month": int(value.start_month),
        "end_year": int(value.end_year),
        "end_month": int(value.end_month),
    }

DEFAULT_MAX_STAGE_ATTEMPTS = 2


def mark_stage_attempt(
    state: WorkflowState,
    stage: WorkflowStep,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    记录某个大阶段被进入的次数。

    返回：
    - attempt_update：正常情况下要写回 state 的更新
    - exceeded_update：如果超过最大次数，返回错误更新；否则为 None
    """
    stage_value = stage.value

    counts = dict(state.get("stage_attempt_counts") or {})
    attempts = counts.get(stage_value, 0) + 1
    counts[stage_value] = attempts

    max_attempts = int(
        state.get("max_stage_attempts") or DEFAULT_MAX_STAGE_ATTEMPTS
    )

    attempt_update = {
        "stage_attempt_counts": counts,
    }

    if attempts > max_attempts:
        message = (
            f"""{stage_value} 阶段已经达到了最大执行次数:({max_attempts}). 为避免无限循环，工作流已进入错误状态。"""
        )

        exceeded_update = {
            **attempt_update,
            "current_stage": WorkflowStep.ERROR.value,
            "status": WorkflowStatus.ERROR.value,
            "target_step": WorkflowStep.ERROR.value,
            "has_error": True,
            "error_message": message,
            "assistant_message": message,
            "needs_supervisor_review": False,
            "execution_history": [
                execution_record(
                    step=stage_value,
                    agent="System",
                    success=False,
                    message=message,
                    metadata={
                        "stage": stage_value,
                        "attempts": attempts,
                        "max_attempts": max_attempts,
                    },
                )
            ],
        }

        return attempt_update, exceeded_update

    return attempt_update, None
