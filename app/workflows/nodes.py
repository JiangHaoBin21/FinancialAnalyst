"""LangGraph 节点实现。"""

from __future__ import annotations

from typing import Any, Optional

from app.utils.report_file_writer import save_markdown_report
from app.workflows.state import (
    PlanStepStatus,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    complete_current_plan_step,
    error_update,
    execution_record,
    fail_current_plan_step,
    is_current_plan_agent,
    resolve_final_report,
    update_current_plan_step_status, mark_stage_attempt,
)



class WorkflowNodes:
    """供 LangGraph 构建器注册的节点集合。"""

    def __init__(
        self,
        supervisor_agent: Any,
        analysis_agent: Optional[Any] = None,
        report_agent: Optional[Any] = None,
        reflection_agent: Optional[Any] = None,
    ):
        self.supervisor_agent = supervisor_agent
        self.analysis_agent = analysis_agent
        self.report_agent = report_agent
        self.reflection_agent = reflection_agent

    # =========================
    # Agent 级节点
    # =========================

    def supervisor_node(self, state: WorkflowState) -> dict:
        """运行 SupervisorAgent，并记录本轮调度结果。"""
        try:
            update = self.supervisor_agent.run(state)
        except Exception as exc:
            update = error_update(f"SupervisorAgent failed: {type(exc).__name__}: {exc}")

        merged = {**state, **update}
        return {
            **update,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.SUPERVISOR.value,
                    agent="SupervisorAgent",
                    success=not merged.get("has_error", False),
                    message=merged.get("assistant_message") or merged.get("error_message") or "",
                    metadata={
                        "task_type": _enum_value(merged.get("task_type")),
                        "next_step": _enum_value(merged.get("next_step")),
                        "needs_user_input": merged.get("needs_user_input", False),
                    },
                )
            ],
        }

    def await_user_input_node(self, state: WorkflowState) -> dict:
        """暂停工作流，等待用户补充缺失信息。"""
        message = state.get("assistant_message") or (
            "I need more information before continuing the analysis."
        )
        return {
            "current_stage": WorkflowStep.AWAIT_USER_INPUT.value,
            "status": WorkflowStatus.NEEDS_USER_INPUT.value,
            "is_finished": False,
            "assistant_message": message,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.AWAIT_USER_INPUT.value,
                    agent="System",
                    success=True,
                    message=message,
                    metadata={"missing_fields": state.get("missing_fields", [])},
                )
            ],
        }

    def analysis_node(self, state: WorkflowState) -> dict:
        """执行分析阶段的计划步骤。"""
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.ANALYSIS,
            expected_agent="AnalysisAgent",
            agent=self.analysis_agent,
            success_status=WorkflowStatus.ANALYSIS_READY,
            default_success_message="AnalysisAgent completed analysis.",
        )

    def report_node(self, state: WorkflowState) -> dict:
        """执行报告生成阶段的计划步骤。"""
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.REPORT,
            expected_agent="ReportAgent",
            agent=self.report_agent,
            success_status=WorkflowStatus.REPORT_READY,
            default_success_message="ReportAgent generated report.",
        )

    def reflection_node(self, state: WorkflowState) -> dict:
        """执行反思检查阶段的计划步骤。"""
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.REFLECTION,
            expected_agent="ReflectionAgent",
            agent=self.reflection_agent,
            success_status=WorkflowStatus.REFLECTION_DONE,
            default_success_message="ReflectionAgent completed review.",
        )





    # =========================
    # 终态节点
    # =========================

    def finish_node(self, state: WorkflowState) -> dict:
        """生成工作流完成状态。"""
        final_report = resolve_final_report(state)
        message = state.get("assistant_message") or "Workflow finished."
        return {
            "current_stage": WorkflowStep.FINISHED.value,
            "status": WorkflowStatus.FINISHED.value,
            "next_step": WorkflowStep.FINISHED.value,
            "is_finished": True,
            "final_report": final_report,
            "final_response": final_report,
            "assistant_message": message,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.FINISHED.value,
                    agent="System",
                    success=True,
                    message=message,
                )
            ],
        }

    def error_node(self, state: WorkflowState) -> dict:
        """生成工作流错误状态。"""
        message = state.get("error_message") or (
            "工作流执行出错."
        )
        return {
            "current_stage": WorkflowStep.ERROR.value,
            "status": WorkflowStatus.ERROR.value,
            "next_step": WorkflowStep.ERROR.value,
            "is_finished": False,
            "assistant_message": message,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.ERROR.value,
                    agent="System",
                    success=False,
                    message=message,
                )
            ],
        }

    # =========================
    # 内部辅助函数
    # =========================

    def _execute_agent_plan_step(
            self,
            state: WorkflowState,
            node_step: WorkflowStep,
            expected_agent: str,
            agent: Any,
            success_status: WorkflowStatus,
            default_success_message: str,
    ) -> dict:
        """
        执行一个受计划约束的 Agent 阶段。

        设计约定：
        1. 普通 Agent 只负责产出业务结果，不负责决定流程跳转；
        2. 当前阶段正常完成后，complete_current_plan_step 会推进计划索引，
           并把 next_step 设置为“计划推荐的下一阶段”；
        3. 当前节点结束后，Graph 通过普通边固定回到 Supervisor；
        4. Supervisor 审查通过则沿用 state["next_step"]，审查不通过则覆盖 next_step。
        """

        if agent is None:
            return self._node_error(
                state=state,
                node_step=node_step,
                agent_name=expected_agent,
                message=f"{expected_agent} is not configured.",
            )

        if not is_current_plan_agent(state, expected_agent):
            return self._node_error(
                state=state,
                node_step=node_step,
                agent_name=expected_agent,
                message=f"Current plan step does not match {expected_agent}.",
            )

        attempt_update, exceeded_update = mark_stage_attempt(
            state=state,
            stage=node_step,
        )

        if exceeded_update is not None:
            return exceeded_update

        # 当前计划步骤开始执行：先标记为 RUNNING
        running_update = {
            **attempt_update,
            "task_plan": update_current_plan_step_status(
                state,
                PlanStepStatus.RUNNING,
            ),
        }
        state_for_agent = {**state, **running_update}

        try:
            # 普通 Agent 只产出业务更新，不负责返回 next_step
            agent_update = agent.run(state_for_agent)
        except Exception as exc:
            return self._node_error(
                state=state_for_agent,
                node_step=node_step,
                agent_name=expected_agent,
                message=f"{expected_agent} failed: {type(exc).__name__}: {exc}",
            )

        merged = {**state_for_agent, **agent_update}

        # 普通 Agent 不通过 next_step 控制流程；
        # 这里只保留 has_error 作为业务失败信号。
        if merged.get("has_error"):
            error_message = (
                    merged.get("error_message")
                    or merged.get("assistant_message")
                    or f"{expected_agent} failed."
            )

            update = {
                "stage_outputs": agent_update,
                **fail_current_plan_step(state_for_agent),
                "status": WorkflowStatus.ERROR.value,
                "current_stage": node_step.value,
                "next_step": WorkflowStep.ERROR.value,
                "has_error": True,
                "error_message": error_message,
                "assistant_message": error_message,
                "last_completed_stage": node_step.value,
                "needs_supervisor_review": False,
            }

            return {
                **update,
                "execution_history": [
                    execution_record(
                        step=node_step.value,
                        agent=expected_agent,
                        success=False,
                        message=error_message,
                    )
                ],
            }

        # 正常完成：
        # 1. 标记当前 plan step 完成；
        # 2. 推进 current_step_index；
        # 3. 让 complete_current_plan_step 计算计划推荐的 next_step。
        plan_update = complete_current_plan_step(state_for_agent)
        planned_next_step = _enum_value(plan_update.get("next_step"))

        message = agent_update.get("assistant_message") or default_success_message
        additional = {}
        if node_step.value == "analysis":
            additional = {
                "analysis_result": agent_update
            }
        elif node_step.value == "report":
            additional = {
                "report_result": agent_update,
                # 新报告只是待 Reflection 审查的草稿。重新生成报告时必须
                # 作废上一轮的最终稿，避免后续错误交付旧修订版本。
                "reflection_result": {},
                "final_report": None,
                "final_response": None,
            }
            save_markdown_report(report_result=agent_update, output_dir="outputs/reports", filename_prefix="report")
        elif node_step.value == "reflection":
            additional = {
                "reflection_result": agent_update,
                "final_report": _approved_report_after_reflection(
                    state_for_agent,
                    agent_update,
                ),
                "final_response": None,
            }

        return {
            **plan_update,
            **additional,
            "stage_outputs": agent_update,
            "current_stage": node_step.value,
            "status": success_status.value,
            "assistant_message": message,

            # 标记：当前大阶段已完成，接下来需要 Supervisor 审查
            "last_completed_stage": node_step.value,

            "execution_history": [
                execution_record(
                    step=node_step.value,
                    agent=expected_agent,
                    success=True,
                    message=message,
                    metadata={
                        "current_step_index": plan_update.get("current_step_index"),
                        "next_step": planned_next_step,
                        "needs_supervisor_review": True,
                        "next_step_semantics": (
                            "plan_suggested_next_step; actual routing is reviewed by Supervisor"
                        ),
                    },
                )
            ],
        }


    def _node_error(
        self,
        state: WorkflowState,
        node_step: WorkflowStep,
        agent_name: str,
        message: str,
    ) -> dict:
        """构造节点失败时的统一状态更新。"""
        return {
            **error_update(message),
            **fail_current_plan_step(state),
            "execution_history": [
                execution_record(
                    step=node_step.value,
                    agent=agent_name,
                    success=False,
                    message=message,
                )
            ],
        }


def _enum_value(value: Any) -> Any:
    """返回枚举的原始值；非枚举对象保持不变。"""
    return value.value if hasattr(value, "value") else value


def _approved_report_after_reflection(
    state: WorkflowState,
    reflection_result: dict[str, Any],
) -> Optional[str]:
    """根据 Reflection 决策生成显式的最终交付报告。"""
    decision = reflection_result.get("decision")

    if decision == "pass_with_minor_revision":
        revised_report = reflection_result.get("final_report_markdown")
        if isinstance(revised_report, str) and revised_report.strip():
            return revised_report
        return None

    if decision == "pass":
        report_result = state.get("report_result")
        if isinstance(report_result, dict):
            report_draft = report_result.get("markdown_report")
            if isinstance(report_draft, str) and report_draft.strip():
                return report_draft

    # 需要回到上游阶段或 Reflection 结果无效时，不保留旧的最终稿。
    return None
