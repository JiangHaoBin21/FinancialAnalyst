"""Workflow state definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskType(str, Enum):
    """顶层任务类型，由 PlanningSkill / Supervisor 决定。"""
    FINANCIAL_ANALYSIS = "financial_analysis"
    UNKNOWN = "unknown"


class WorkflowStep(str, Enum):
    """工作流节点名 / 当前阶段标记。"""
    SUPERVISOR = "supervisor"
    AWAIT_USER_INPUT = "await_user_input"
    DATA = "data"
    ANALYSIS = "analysis"
    REPORT = "report"
    REFLECTION = "reflection"
    FINISHED = "finished"
    ERROR = "error"


class OutputMode(str, Enum):
    """报告输出形式。"""
    REPORT = "report"
    SUMMARY = "summary"


class PlanStepStatus(str, Enum):
    """计划步骤执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """工作流整体状态。"""
    INIT = "init"
    NEEDS_USER_INPUT = "needs_user_input"
    READY_FOR_EXECUTION = "ready_for_execution"
    DATA_READY = "data_ready"
    ANALYSIS_READY = "analysis_ready"
    REPORT_READY = "report_ready"
    REFLECTION_DONE = "reflection_done"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class PlanStep:
    """
    Planner 生成的单个计划步骤。
    注意：
    - 这是“计划层”的 step，不是 graph node 本身
    - graph/node 会根据 plan step 的 agent 来决定执行哪个节点
    """
    step_id: int
    agent: str
    action: str
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING


@dataclass
class ExecutionRecord:
    """
    记录每个节点/Agent的一次执行情况，便于调试、回放、面试展示。
    """
    step: str
    agent: str
    success: bool
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """
    多 Agent 财报分析系统的共享工作流状态。

    设计原则：
    1. 所有 Agent 都围绕这个 state 读写
    2. supervisor 负责写入初始规划结果
    3. nodes / graph 根据 task_plan + current_step_index 推进流程
    4. 正常主流程尽量按 plan 驱动，而不是硬编码顺序
    """

    # =========================
    # 1. 用户输入层
    # =========================
    user_query: str

    # =========================
    # 2. 意图识别 / 规划层
    # =========================
    task_type: TaskType = TaskType.UNKNOWN
    company_name: Optional[str] = None
    ts_code: Optional[str] = None
    time_range: Optional[str] = None
    analysis_focus: Optional[str] = None
    output_mode: OutputMode = OutputMode.REPORT

    planner_message: Optional[str] = None
    raw_planner_response: Optional[str] = None

    needs_user_input: bool = False
    missing_fields: list[str] = field(default_factory=list)

    task_plan: list[PlanStep] = field(default_factory=list)

    # 计划执行游标：用于 plan-driven workflow
    current_step_index: int = 0
    completed_step_ids: list[int] = field(default_factory=list)

    # =========================
    # 3. Data Agent 结果层
    # =========================
    company_profile: dict[str, Any] = field(default_factory=dict)
    financial_data: dict[str, Any] = field(default_factory=dict)
    data_summary: dict[str, Any] = field(default_factory=dict)

    # =========================
    # 4. Analysis Agent 结果层
    # =========================
    analysis_result: dict[str, Any] = field(default_factory=dict)
    analysis_summary: Optional[str] = None

    # =========================
    # 5. Report Agent 结果层
    # =========================
    report_draft: Optional[str] = None
    report_sections: dict[str, Any] = field(default_factory=dict)
    final_report: Optional[str] = None

    # =========================
    # 6. Reflection Agent 结果层
    # =========================
    reflection_result: dict[str, Any] = field(default_factory=dict)
    needs_revision: bool = False
    replan_required: bool = False

    # =========================
    # 7. 流程控制层
    # =========================
    current_stage: WorkflowStep = WorkflowStep.SUPERVISOR
    next_step: Optional[WorkflowStep] = None
    status: WorkflowStatus = WorkflowStatus.INIT

    is_finished: bool = False
    has_error: bool = False
    error_message: Optional[str] = None

    # 给用户/前端看的当前消息
    assistant_message: Optional[str] = None

    # =========================
    # 8. 可观测性 / 调试层
    # =========================
    execution_history: list[ExecutionRecord] = field(default_factory=list)

    # =========================
    # 9. 最终输出层
    # =========================
    final_response: Optional[str] = None

    # =========================
    # 10. 基础辅助方法
    # =========================

    def add_execution_record(
        self,
        step: str,
        agent: str,
        success: bool,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """追加一条执行记录。"""
        self.execution_history.append(
            ExecutionRecord(
                step=step,
                agent=agent,
                success=success,
                message=message,
                metadata=metadata or {},
            )
        )

    def set_error(self, message: str) -> None:
        """设置错误状态。"""
        self.has_error = True
        self.error_message = message
        self.status = WorkflowStatus.ERROR
        self.current_stage = WorkflowStep.ERROR
        self.next_step = WorkflowStep.ERROR
        self.is_finished = False

    def mark_finished(self, final_response: Optional[str] = None) -> None:
        """标记工作流完成。"""
        self.is_finished = True
        self.status = WorkflowStatus.FINISHED
        self.current_stage = WorkflowStep.FINISHED
        self.next_step = WorkflowStep.FINISHED
        if final_response is not None:
            self.final_response = final_response

    def reset_for_replan(self) -> None:
        """
        当 Reflection 或其他节点要求重新规划时，可调用本方法。
        注意：保留已有中间结果是否合理，可按后续需求再细化。
        """
        self.replan_required = False
        self.needs_user_input = False
        self.missing_fields = []
        self.task_plan = []
        self.current_step_index = 0
        self.completed_step_ids = []
        self.current_stage = WorkflowStep.SUPERVISOR
        self.next_step = WorkflowStep.SUPERVISOR
        self.status = WorkflowStatus.INIT

    # =========================
    # 11. plan-driven workflow 辅助方法
    # =========================

    def get_current_plan_step(self) -> Optional[PlanStep]:
        """获取当前待执行的计划步骤。"""
        if self.current_step_index < 0 or self.current_step_index >= len(self.task_plan):
            return None
        return self.task_plan[self.current_step_index]

    def mark_current_plan_step_running(self) -> None:
        """将当前计划步骤标记为 running。"""
        step = self.get_current_plan_step()
        if step is not None:
            step.status = PlanStepStatus.RUNNING

    def mark_current_plan_step_done(self) -> None:
        """将当前计划步骤标记为 done，并记录完成列表。"""
        step = self.get_current_plan_step()
        if step is not None:
            step.status = PlanStepStatus.DONE
            if step.step_id not in self.completed_step_ids:
                self.completed_step_ids.append(step.step_id)

    def mark_current_plan_step_failed(self) -> None:
        """将当前计划步骤标记为 failed。"""
        step = self.get_current_plan_step()
        if step is not None:
            step.status = PlanStepStatus.FAILED

    def advance_plan_step(self) -> None:
        """推进计划游标到下一步。"""
        self.current_step_index += 1

    def has_remaining_plan_steps(self) -> bool:
        """是否还有剩余计划步骤。"""
        return self.current_step_index < len(self.task_plan)

    def set_next_step_from_plan(self) -> None:
        """
        根据当前 plan cursor 推导 next_step。
        仅用于正常主流程推进。
        异常、中断、等待用户输入时，应由节点显式覆盖 next_step。
        """
        step = self.get_current_plan_step()
        if step is None:
            self.next_step = WorkflowStep.FINISHED
            return

        agent_to_workflow_step = {
            "DataAgent": WorkflowStep.DATA,
            "AnalysisAgent": WorkflowStep.ANALYSIS,
            "ReportAgent": WorkflowStep.REPORT,
            "ReflectionAgent": WorkflowStep.REFLECTION,
        }

        self.next_step = agent_to_workflow_step.get(step.agent, WorkflowStep.ERROR)