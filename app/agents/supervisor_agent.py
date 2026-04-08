"""Supervisor agent orchestration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from app.skills.planning_skills import PlanningResult, PlanningSkill
from app.workflows.state import (
    PlanStep,
    TaskType,
    WorkflowState,
    WorkflowStep,
)


class SupervisorAgent:
    """
    多 Agent 财报分析系统中的 Supervisor Agent

    职责：
    1. 调用 PlanningSkill 进行任务理解与规划
    2. 将规划结果写回 WorkflowState
    3. 生成 task_plan
    4. 决定流程是否继续，或因信息不足而结束

    不负责：
    - 不直接调用 OpenAI SDK
    - 不直接获取财务数据
    - 不直接分析财务数据
    - 不直接生成最终财报报告
    """

    AGENT_NAME = "SupervisorAgent"

    def __init__(self, planning_skill: PlanningSkill):
        self.planning_skill = planning_skill

    def run(self, state: WorkflowState) -> WorkflowState:
        """
        执行 Supervisor 的一次任务规划。

        输入：
        - state.user_query

        输出：
        - 更新 state.task_type / company_name / ts_code / time_range
        - 更新 state.task_plan / planner_message / next_step
        - 如信息不足，则直接写 final_response 并结束流程
        """
        try:
            planning_result = self.planning_skill.plan_financial_task(
                user_query=state.user_query
            )

            self._apply_planning_result(state, planning_result)
            self._record_success(state, planning_result)

            return state

        except Exception as e:
            state.set_error(f"SupervisorAgent 执行失败: {str(e)}")
            state.add_execution_record(
                step=WorkflowStep.SUPERVISOR.value,
                agent=self.AGENT_NAME,
                success=False,
                message=f"任务规划失败: {str(e)}",
                metadata={},
            )
            return state

    def _apply_planning_result(
        self,
        state: WorkflowState,
        result: PlanningResult,
    ) -> None:
        """
        将 PlanningSkill 的输出安全写回 WorkflowState。
        """
        state.task_type = self._map_task_type(result.task_type)
        state.company_name = result.company_name
        state.ts_code = result.ts_code
        state.time_range = result.time_range
        state.planner_message = result.planner_message

        state.task_plan = [
            PlanStep(
                step_id=step.step_id,
                agent=step.agent,
                action=step.action,
                description=step.description,
                status="pending",
            )
            for step in result.task_plan
        ]

        state.current_step = WorkflowStep.SUPERVISOR

        if result.needs_user_input:
            state.next_step = None
            state.final_response = self._build_missing_info_response(result)
            state.is_finished = True
            state.needs_revision = False
            state.current_step = WorkflowStep.FINISHED
            return

        mapped_next_step = self._map_workflow_step(result.next_step)
        state.next_step = mapped_next_step
        state.is_finished = False
        state.final_response = None

    def _record_success(
        self,
        state: WorkflowState,
        result: PlanningResult,
    ) -> None:
        """
        记录一次成功执行的轨迹。
        """
        state.add_execution_record(
            step=WorkflowStep.SUPERVISOR.value,
            agent=self.AGENT_NAME,
            success=True,
            message="任务理解与规划完成。",
            metadata={
                "task_type": result.task_type,
                "company_name": result.company_name,
                "ts_code": result.ts_code,
                "time_range": result.time_range,
                "next_step": result.next_step,
                "needs_user_input": result.needs_user_input,
                "missing_fields": result.missing_fields,
                "plan_steps_count": len(result.task_plan),
            },
        )

    def _map_task_type(self, task_type: str) -> TaskType:
        """
        将 skill 层字符串 task_type 映射为 state 层枚举。
        """
        mapping = {
            "analyze_financial_report": TaskType.ANALYZE_FINANCIAL_REPORT,
            "generate_report": TaskType.GENERATE_REPORT,
            "unknown": TaskType.UNKNOWN,
        }
        return mapping.get(task_type, TaskType.UNKNOWN)

    def _map_workflow_step(self, step: str) -> WorkflowStep:
        """
        将 skill 层字符串 next_step 映射为 state 层枚举。
        """
        mapping = {
            "supervisor": WorkflowStep.SUPERVISOR,
            "data": WorkflowStep.DATA,
            "analysis": WorkflowStep.ANALYSIS,
            "report": WorkflowStep.REPORT,
            "reflection": WorkflowStep.REFLECTION,
            "finished": WorkflowStep.FINISHED,
            "error": WorkflowStep.ERROR,
        }
        return mapping.get(step, WorkflowStep.ERROR)

    def _build_missing_info_response(self, result: PlanningResult) -> str:
        """
        当用户输入信息不足时，构造对用户友好的提示。
        """
        if result.task_type == "unknown":
            return (
                "我暂时没有识别出明确的财报分析任务。"
                "你可以告诉我公司名称或 ts_code，以及想分析的时间范围。"
            )

        if "company_name_or_ts_code" in result.missing_fields:
            return (
                "我已经识别到这是一个财报分析任务，但还缺少公司名称或 ts_code。"
                "例如你可以告诉我“平安银行”或“000001.SZ”。"
            )

        if "task_description" in result.missing_fields:
            return (
                "当前任务描述还不够明确。"
                "你可以告诉我想分析哪家公司、哪个时间范围，以及希望输出分析还是报告。"
            )

        return "当前任务信息还不完整，请补充后再继续。"