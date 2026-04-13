"""Supervisor Agent：负责接收用户请求、调用规划器、写回状态、决定流程入口。"""

from __future__ import annotations

from app.skills.planning.planning_skill import PlanningSkill
from app.domain.models import PlanningResult, PlanningStep as SkillPlanningStep
from app.workflows.state import (
    WorkflowState,
    TaskType,
    WorkflowStep,
    WorkflowStatus,
    OutputMode,
    PlanStep,
)


class SupervisorAgent:
    """
    SupervisorAgent 是系统的任务调度入口。

    职责：
    1. 接收用户输入
    2. 调用 PlanningSkill 做任务理解与高层规划
    3. 将规划结果写回 WorkflowState
    4. 生成缺失信息追问
    5. 初始化 plan-driven workflow 的执行入口

    不负责：
    - 不直接拉取数据
    - 不直接做财务分析
    - 不直接生成报告正文
    """

    def __init__(self, planning_skill: PlanningSkill):
        self.planning_skill = planning_skill

    def run(self, state: WorkflowState) -> WorkflowState:
        user_query = getattr(state, "user_query", None)
        if not user_query or not str(user_query).strip():
            return self._handle_empty_query(state)

        try:
            # 方案 B：planning_skill 内部已经串了 prompt_builder / parser / policy
            planning_result = self.planning_skill.plan_financial_task(user_query=user_query)
        except Exception as e:
            return self._handle_planning_exception(state, e)

        self._write_planning_result_to_state(state, planning_result)

        if planning_result.needs_user_input:
            clarification_message = self._build_clarification_message(planning_result)
            self._mark_waiting_for_user_input(
                state=state,
                assistant_message=clarification_message,
            )
            return state

        self._mark_ready_for_execution(state, planning_result)
        return state

    def _write_planning_result_to_state(
        self,
        state: WorkflowState,
        planning_result: PlanningResult,
    ) -> None:
        """
        将planner规划好的result写回到state当中

        :param state: 共享state状态信息
        :param planning_result: planner skill规划好的result结果
        :return: None
        """
        state.task_type = self._to_task_type(planning_result.task_type)
        state.company_name = planning_result.company_name
        state.ts_code = planning_result.ts_code
        state.time_range = planning_result.time_range
        state.analysis_focus = planning_result.analysis_focus
        state.output_mode = self._to_output_mode(planning_result.output_mode)

        state.planner_message = planning_result.planner_message
        state.needs_user_input = planning_result.needs_user_input
        state.missing_fields = list(planning_result.missing_fields or [])
        state.raw_planner_response = planning_result.raw_response

        state.task_plan = [self._to_state_plan_step(step) for step in planning_result.task_plan]

        state.current_step_index = 0
        state.completed_step_ids = []

        state.current_stage = WorkflowStep.SUPERVISOR
        state.next_step = None

        state.has_error = False
        state.error_message = None
        state.is_finished = False

    def _mark_waiting_for_user_input(
        self,
        state: WorkflowState,
        assistant_message: str,
    ) -> None:
        state.status = WorkflowStatus.NEEDS_USER_INPUT
        state.current_stage = WorkflowStep.AWAIT_USER_INPUT
        state.next_step = WorkflowStep.AWAIT_USER_INPUT
        state.assistant_message = assistant_message
        state.is_finished = False
        state.has_error = False
        state.error_message = None

    def _mark_ready_for_execution(
        self,
        state: WorkflowState,
        planning_result: PlanningResult,
    ) -> None:
        state.status = WorkflowStatus.READY_FOR_EXECUTION
        state.current_stage = WorkflowStep.SUPERVISOR
        state.assistant_message = self._build_ready_message(planning_result)
        state.is_finished = False
        state.has_error = False
        state.error_message = None

        state.set_next_step_from_plan()

        if state.next_step == WorkflowStep.ERROR:
            state.has_error = True
            state.status = WorkflowStatus.ERROR
            state.error_message = "规划结果中的 task_plan 无法映射到合法工作流步骤。"
            state.assistant_message = state.error_message

    def _handle_empty_query(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.NEEDS_USER_INPUT
        state.current_stage = WorkflowStep.AWAIT_USER_INPUT
        state.next_step = WorkflowStep.AWAIT_USER_INPUT
        state.needs_user_input = True
        state.missing_fields = ["task_description"]
        state.assistant_message = "请告诉我你想分析哪家公司，以及希望我做什么，例如：分析宁德时代近三年的财务表现。"
        state.is_finished = False
        state.has_error = False
        state.error_message = None
        return state

    def _handle_planning_exception(self, state: WorkflowState, exc: Exception) -> WorkflowState:
        state.status = WorkflowStatus.ERROR
        state.current_stage = WorkflowStep.SUPERVISOR
        state.next_step = WorkflowStep.ERROR
        state.needs_user_input = False
        state.assistant_message = "任务规划阶段出现异常，暂时无法继续。"
        state.error_message = f"{type(exc).__name__}: {str(exc)}"
        state.has_error = True
        state.is_finished = False
        return state

    def _build_clarification_message(self, planning_result: PlanningResult) -> str:
        missing = set(planning_result.missing_fields or [])

        if "company_name_or_ts_code" in missing:
            return "请告诉我你想分析的公司名称或股票代码，例如：宁德时代 或 300750.SZ。"

        prompts: list[str] = []

        if "company_name" in missing:
            prompts.append("公司名称")
        if "ts_code" in missing:
            prompts.append("股票代码")
        if "time_range" in missing:
            prompts.append("分析时间范围")
        if "analysis_focus" in missing:
            prompts.append("分析重点")
        if "task_description" in missing:
            prompts.append("你的具体需求")

        if prompts:
            joined = "、".join(prompts)
            return f"为了继续处理你的请求，请补充：{joined}。"

        return "我还需要你补充一些信息，才能继续为你规划后续分析流程。"

    def _build_ready_message(self, planning_result: PlanningResult) -> str:
        company = planning_result.company_name or planning_result.ts_code or "目标公司"
        time_range_text = self._format_time_range(planning_result.time_range)
        focus = planning_result.analysis_focus or "综合财务表现"
        output_mode = planning_result.output_mode

        if output_mode == "summary":
            return f"已完成任务规划，接下来将围绕 {company} 的 {time_range_text} {focus}进行分析，并输出简要总结。"

        return f"已完成任务规划，接下来将围绕 {company} 的 {time_range_text} {focus}进行分析，并生成报告。"

    @staticmethod
    def _format_time_range(time_range) -> str:
        if not time_range:
            return "默认时间范围"
        return f"{time_range.start_year}.{time_range.start_month:02d} - {time_range.end_year}.{time_range.end_month:02d}"

    @staticmethod
    def _to_task_type(value: str) -> TaskType:
        if value == "financial_analysis":
            return TaskType.FINANCIAL_ANALYSIS
        return TaskType.UNKNOWN

    @staticmethod
    def _to_output_mode(value: str) -> OutputMode:
        if value == "summary":
            return OutputMode.SUMMARY
        return OutputMode.REPORT

    @staticmethod
    def _to_state_plan_step(step: SkillPlanningStep) -> PlanStep:
        return PlanStep(
            step_id=step.step_id,
            agent=step.agent,
            action=step.action,
            description=step.description,
        )