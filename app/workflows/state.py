"""Workflow state definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskType(str, Enum):
    """任务类型，由supervisor决定是哪一类任务类型"""
    ANALYZE_FINANCIAL_REPORT = "analyze_financial_report"
    GENERATE_REPORT = "generate_report"
    UNKNOWN = "unknown"


class WorkflowStep(str, Enum):
    """工作流步骤 / 节点名,用于记录当前运行到哪个节点"""
    SUPERVISOR = "supervisor"
    DATA = "data"
    ANALYSIS = "analysis"
    REPORT = "report"
    REFLECTION = "reflection"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class PlanStep:
    """
    Supervisor 生成的单个计划步骤
    """
    step_id: int
    agent: str
    action: str
    description: str
    status: str = "pending"  # pending / running / done / failed


@dataclass
class ExecutionRecord:
    """
    记录每个节点/Agent的一次执行情况，便于调试、回放、面试展示
    """
    step: str
    agent: str
    success: bool
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """
    多 Agent 财报分析系统的共享工作流状态

    说明：
    - 所有 Agent 都围绕这个 state 读写
    - nodes.py 负责调用 Agent，并更新 state
    - graph.py 负责根据 state 决定下一步流转
    """

    # =========================
    # 1. 用户输入层
    # =========================
    user_query: str

    # 用户问题中提取出的关键信息
    task_type: TaskType = TaskType.UNKNOWN
    ts_code: Optional[str] = None
    company_name: Optional[str] = None
    time_range: Optional[str] = None  # 如 "近3年" / "2021-2024"

    # =========================
    # 2. Supervisor 规划层
    # =========================
    task_plan: list[PlanStep] = field(default_factory=list)
    planner_message: Optional[str] = None

    # =========================
    # 3. Data Agent 结果层
    # =========================
    company_profile: dict[str, Any] = field(default_factory=dict)
    financial_data: dict[str, Any] = field(default_factory=dict)
    # 例如：
    # {
    #   "income": [...],
    #   "balance_sheet": [...],
    #   "cashflow": [...],
    #   "fina_indicator": [...]
    # }

    data_summary: dict[str, Any] = field(default_factory=dict)
    # 例如：
    # {
    #   "income_count": 12,
    #   "balance_count": 12,
    #   "cashflow_count": 12,
    #   "indicator_count": 12
    # }

    # =========================
    # 4. Analysis Agent 结果层
    # =========================
    analysis_result: dict[str, Any] = field(default_factory=dict)
    # 例如：
    # {
    #   "profitability": {...},
    #   "solvency": {...},
    #   "cashflow_health": {...},
    #   "growth": {...},
    #   "highlights": [...],
    #   "risks": [...]
    # }

    analysis_summary: Optional[str] = None

    # =========================
    # 5. Report Agent 结果层
    # =========================
    report_draft: Optional[str] = None
    report_sections: dict[str, Any] = field(default_factory=dict)

    # =========================
    # 6. Reflection Agent 结果层
    # =========================
    reflection_result: dict[str, Any] = field(default_factory=dict)
    # 例如：
    # {
    #   "is_complete": True,
    #   "missing_dimensions": [],
    #   "suggestions": []
    # }

    needs_revision: bool = False

    # =========================
    # 7. 流程控制层
    # =========================
    current_step: WorkflowStep = WorkflowStep.SUPERVISOR
    next_step: Optional[WorkflowStep] = None

    is_finished: bool = False
    has_error: bool = False
    error_message: Optional[str] = None

    # =========================
    # 8. 可观测性 / 调试层
    # =========================
    execution_history: list[ExecutionRecord] = field(default_factory=list)

    # =========================
    # 9. 最终输出层
    # =========================
    final_response: Optional[str] = None

    def add_execution_record(
        self,
        step: str,
        agent: str,
        success: bool,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """追加一条执行记录"""
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
        """设置错误状态"""
        self.has_error = True
        self.error_message = message
        self.current_step = WorkflowStep.ERROR
        self.next_step = None
        self.is_finished = False

    def mark_finished(self, final_response: Optional[str] = None) -> None:
        """标记工作流完成"""
        self.is_finished = True
        self.current_step = WorkflowStep.FINISHED
        self.next_step = None
        if final_response is not None:
            self.final_response = final_response
