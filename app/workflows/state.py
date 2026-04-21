"""LangGraph-native workflow state definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from app.domain.models import TimeRange


def append_list(left: Optional[list[Any]], right: Optional[list[Any]]) -> list[Any]:
    """Reducer for fields written by parallel LangGraph nodes."""
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
    """A high-level agent step produced by the supervisor planner."""

    step_id: int
    agent: str
    action: str
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING


@dataclass
class ExecutionRecord:
    """Observable execution record for graph nodes and agents."""

    step: str
    agent: str
    success: bool
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataPartResult:
    """Result emitted by a parallel data fetch node."""

    part_name: str
    payload: Any
    success: bool = True
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowState(TypedDict, total=False):
    # User input
    user_query: str

    # Supervisor / planning layer
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

    # Data planning and fan-out layer
    required_data_parts: list[str]
    data_part_results: Annotated[list[DataPartResult], append_list]
    data_fetch_errors: Annotated[list[str], append_list]

    # Data merge results
    company_profile: dict[str, Any]
    financial_data: dict[str, Any]
    data_summary: dict[str, Any]

    # Analysis results
    analysis_result: dict[str, Any]
    analysis_summary: Optional[str]

    # Report results
    report_draft: Optional[str]
    report_sections: dict[str, Any]
    final_report: Optional[str]

    # Reflection results
    reflection_result: dict[str, Any]
    needs_revision: bool
    replan_required: bool

    # Flow control
    current_stage: WorkflowStep
    next_step: Optional[WorkflowStep]
    status: WorkflowStatus
    is_finished: bool
    has_error: bool
    error_message: Optional[str]
    assistant_message: Optional[str]

    # Observability
    execution_history: Annotated[list[ExecutionRecord], append_list]

    # Final output
    final_response: Optional[str]


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
    """Create a full initial state so graph nodes can use safe defaults."""
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
    return ExecutionRecord(
        step=step,
        agent=agent,
        success=success,
        message=message,
        metadata=metadata or {},
    )


def get_current_plan_step(state: WorkflowState) -> Optional[PlanStep]:
    index = state.get("current_step_index", 0)
    task_plan = state.get("task_plan", [])
    if index < 0 or index >= len(task_plan):
        return None
    return task_plan[index]


def update_current_plan_step_status(
    state: WorkflowState,
    status: PlanStepStatus,
) -> list[PlanStep]:
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
    task_plan = update_current_plan_step_status(state, PlanStepStatus.DONE)
    step = get_current_plan_step(state)
    completed_step_ids = list(state.get("completed_step_ids", []))
    if step is not None and step.step_id not in completed_step_ids:
        completed_step_ids.append(step.step_id)

    current_step_index = state.get("current_step_index", 0) + 1
    next_step = next_workflow_step(task_plan, current_step_index)
    return {
        "task_plan": task_plan,
        "completed_step_ids": completed_step_ids,
        "current_step_index": current_step_index,
        "next_step": next_step,
    }


def fail_current_plan_step(state: WorkflowState) -> dict[str, Any]:
    return {"task_plan": update_current_plan_step_status(state, PlanStepStatus.FAILED)}


def next_workflow_step(
    task_plan: list[PlanStep],
    current_step_index: int,
) -> WorkflowStep:
    if current_step_index < 0 or current_step_index >= len(task_plan):
        return WorkflowStep.FINISHED

    agent_to_workflow_step = {
        "DataAgent": WorkflowStep.DATA,
        "AnalysisAgent": WorkflowStep.ANALYSIS,
        "ReportAgent": WorkflowStep.REPORT,
        "ReflectionAgent": WorkflowStep.REFLECTION,
    }
    return agent_to_workflow_step.get(task_plan[current_step_index].agent, WorkflowStep.ERROR)


def is_current_plan_agent(state: WorkflowState, expected_agent: str) -> bool:
    step = get_current_plan_step(state)
    return step is not None and step.agent == expected_agent


def error_update(message: str) -> dict[str, Any]:
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
    if is_dataclass(obj):
        return normalize_for_json(asdict(obj))
    if isinstance(obj, dict):
        return {k: normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_for_json(v) for v in obj]
    if hasattr(obj, "value"):
        return obj.value
    return obj
