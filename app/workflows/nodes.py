"""Workflow nodes: 将各个 Agent/阶段包装成 plan-driven 的执行节点。"""

from __future__ import annotations

from typing import Any, Optional

from app.workflows.state import WorkflowState, WorkflowStep, WorkflowStatus


class WorkflowNodes:
    """
    工作流节点集合（plan-driven 版本）。

    设计原则：
    1. 正常主流程按照 task_plan + current_step_index 推进
    2. node 不硬编码业务顺序
    3. node 只负责：
       - 调用对应 agent
       - 标记当前计划步骤状态
       - 推进 plan cursor
       - 在异常/中断时显式覆盖 next_step
    """

    def __init__(
        self,
        supervisor_agent: Any,
        data_agent: Optional[Any] = None,
        analysis_agent: Optional[Any] = None,
        report_agent: Optional[Any] = None,
        reflection_agent: Optional[Any] = None,
    ):
        self.supervisor_agent = supervisor_agent
        self.data_agent = data_agent
        self.analysis_agent = analysis_agent
        self.report_agent = report_agent
        self.reflection_agent = reflection_agent

    # =========================
    # 1) Supervisor Node
    # =========================

    def supervisor_node(self, state: WorkflowState) -> WorkflowState:
        """
        任务入口节点：
        - 调用 SupervisorAgent
        - 完成任务理解、规划、状态写回
        - 如果规划成功，由 Supervisor 初始化 next_step
        """
        state.current_stage = WorkflowStep.SUPERVISOR

        try:
            state = self.supervisor_agent.run(state)
            state.add_execution_record(
                step=WorkflowStep.SUPERVISOR.value,
                agent="SupervisorAgent",
                success=(not state.has_error),
                message=state.assistant_message or "",
                metadata={
                    "task_type": state.task_type.value if hasattr(state.task_type, "value") else str(state.task_type),
                    "next_step": state.next_step.value if getattr(state, "next_step", None) else None,
                    "needs_user_input": state.needs_user_input,
                },
            )
            return state
        except Exception as e:
            state.set_error(f"SupervisorAgent 执行异常: {type(e).__name__}: {str(e)}")
            state.assistant_message = "任务规划阶段出现异常，暂时无法继续。"
            state.add_execution_record(
                step=WorkflowStep.SUPERVISOR.value,
                agent="SupervisorAgent",
                success=False,
                message=state.error_message or "",
            )
            return state

    # =========================
    # 2) Await User Input Node
    # =========================

    def await_user_input_node(self, state: WorkflowState) -> WorkflowState:
        """
        等待用户补充信息节点。
        """
        state.current_stage = WorkflowStep.AWAIT_USER_INPUT
        state.status = WorkflowStatus.NEEDS_USER_INPUT
        state.is_finished = False

        if not state.assistant_message:
            state.assistant_message = "我还需要你补充一些信息，才能继续分析。"

        state.add_execution_record(
            step=WorkflowStep.AWAIT_USER_INPUT.value,
            agent="System",
            success=True,
            message=state.assistant_message,
            metadata={
                "missing_fields": state.missing_fields,
            },
        )
        return state

    # =========================
    # 3) Data Node
    # =========================

    def data_node(self, state: WorkflowState) -> WorkflowState:
        """
        数据准备节点：
        - 验证当前计划步骤是否匹配 DataAgent
        - 调用 DataAgent
        - 成功后推进 plan cursor，并从 plan 推导 next_step
        """
        state.current_stage = WorkflowStep.DATA

        if self.data_agent is None:
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="DataAgent 未配置，无法执行数据准备节点。",
            )

        if not self._validate_current_plan_step(state, expected_agent="DataAgent"):
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="当前计划步骤与 DataAgent 不匹配，无法执行 data_node。",
            )

        return self._execute_plan_step(
            state=state,
            node_step=WorkflowStep.DATA,
            agent_name="DataAgent",
            agent=self.data_agent,
            success_status=WorkflowStatus.DATA_READY,
            default_success_message="已完成财务数据准备。",
        )

    # =========================
    # 4) Analysis Node
    # =========================

    def analysis_node(self, state: WorkflowState) -> WorkflowState:
        """
        分析节点：
        - 验证当前计划步骤是否匹配 AnalysisAgent
        - 调用 AnalysisAgent
        - 成功后推进 plan cursor，并从 plan 推导 next_step
        """
        state.current_stage = WorkflowStep.ANALYSIS

        if self.analysis_agent is None:
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.ANALYSIS,
                agent_name="AnalysisAgent",
                message="AnalysisAgent 未配置，无法执行分析节点。",
            )

        if not self._validate_current_plan_step(state, expected_agent="AnalysisAgent"):
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.ANALYSIS,
                agent_name="AnalysisAgent",
                message="当前计划步骤与 AnalysisAgent 不匹配，无法执行 analysis_node。",
            )

        return self._execute_plan_step(
            state=state,
            node_step=WorkflowStep.ANALYSIS,
            agent_name="AnalysisAgent",
            agent=self.analysis_agent,
            success_status=WorkflowStatus.ANALYSIS_READY,
            default_success_message="已完成财务分析。",
        )

    # =========================
    # 5) Report Node
    # =========================

    def report_node(self, state: WorkflowState) -> WorkflowState:
        """
        报告节点：
        - 验证当前计划步骤是否匹配 ReportAgent
        - 调用 ReportAgent
        - 成功后推进 plan cursor，并从 plan 推导 next_step
        """
        state.current_stage = WorkflowStep.REPORT

        if self.report_agent is None:
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.REPORT,
                agent_name="ReportAgent",
                message="ReportAgent 未配置，无法执行报告节点。",
            )

        if not self._validate_current_plan_step(state, expected_agent="ReportAgent"):
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.REPORT,
                agent_name="ReportAgent",
                message="当前计划步骤与 ReportAgent 不匹配，无法执行 report_node。",
            )

        return self._execute_plan_step(
            state=state,
            node_step=WorkflowStep.REPORT,
            agent_name="ReportAgent",
            agent=self.report_agent,
            success_status=WorkflowStatus.REPORT_READY,
            default_success_message="已完成报告生成。",
        )

    # =========================
    # 6) Reflection Node
    # =========================

    def reflection_node(self, state: WorkflowState) -> WorkflowState:
        """
        审查节点：
        - 验证当前计划步骤是否匹配 ReflectionAgent
        - 调用 ReflectionAgent
        - 支持：
          1. 正常完成后继续按 plan 推进
          2. 要求重规划时跳回 supervisor
          3. 要求修订时跳回 analysis/report（由 ReflectionAgent 预先写入 next_step）
        """
        state.current_stage = WorkflowStep.REFLECTION

        if self.reflection_agent is None:
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.REFLECTION,
                agent_name="ReflectionAgent",
                message="ReflectionAgent 未配置，无法执行审查节点。",
            )

        if not self._validate_current_plan_step(state, expected_agent="ReflectionAgent"):
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.REFLECTION,
                agent_name="ReflectionAgent",
                message="当前计划步骤与 ReflectionAgent 不匹配，无法执行 reflection_node。",
            )

        state.mark_current_plan_step_running()

        try:
            state = self.reflection_agent.run(state)
        except Exception as e:
            state.mark_current_plan_step_failed()
            return self._mark_node_error(
                state=state,
                node_step=WorkflowStep.REFLECTION,
                agent_name="ReflectionAgent",
                message=f"ReflectionAgent 执行异常: {type(e).__name__}: {str(e)}",
            )

        # 1) ReflectionAgent 要求重规划
        if getattr(state, "replan_required", False):
            state.mark_current_plan_step_done()
            state.status = WorkflowStatus.READY_FOR_EXECUTION
            state.current_stage = WorkflowStep.REFLECTION
            state.next_step = WorkflowStep.SUPERVISOR
            state.assistant_message = state.assistant_message or "审查完成，发现需要重新规划，正在返回 supervisor。"
            state.add_execution_record(
                step=WorkflowStep.REFLECTION.value,
                agent="ReflectionAgent",
                success=True,
                message=state.assistant_message,
                metadata={"replan_required": True},
            )
            return state

        # 2) ReflectionAgent 显式要求回退修订
        if state.next_step in {WorkflowStep.ANALYSIS, WorkflowStep.REPORT}:
            state.mark_current_plan_step_done()
            state.status = WorkflowStatus.REFLECTION_DONE
            state.assistant_message = state.assistant_message or "审查完成，发现需要修订，正在回退到指定节点。"
            state.add_execution_record(
                step=WorkflowStep.REFLECTION.value,
                agent="ReflectionAgent",
                success=True,
                message=state.assistant_message,
                metadata={"fallback_to": state.next_step.value},
            )
            return state

        # 3) 正常按 plan 推进
        state.mark_current_plan_step_done()
        state.advance_plan_step()
        state.set_next_step_from_plan()
        state.status = WorkflowStatus.REFLECTION_DONE
        state.assistant_message = state.assistant_message or "审查已完成。"

        state.add_execution_record(
            step=WorkflowStep.REFLECTION.value,
            agent="ReflectionAgent",
            success=True,
            message=state.assistant_message,
            metadata={
                "next_step": state.next_step.value if state.next_step else None,
                "current_step_index": state.current_step_index,
            },
        )
        return state

    # =========================
    # 7) Finish Node
    # =========================

    def finish_node(self, state: WorkflowState) -> WorkflowState:
        """
        流程结束节点。
        """
        state.current_stage = WorkflowStep.FINISHED
        state.mark_finished(final_response=state.final_report or state.final_response)
        if not state.assistant_message:
            state.assistant_message = "任务已完成。"

        state.add_execution_record(
            step=WorkflowStep.FINISHED.value,
            agent="System",
            success=True,
            message=state.assistant_message,
        )
        return state

    # =========================
    # 8) Error Node
    # =========================

    def error_node(self, state: WorkflowState) -> WorkflowState:
        """
        错误收敛节点。
        """
        state.current_stage = WorkflowStep.ERROR
        state.status = WorkflowStatus.ERROR
        state.next_step = WorkflowStep.ERROR
        state.is_finished = False

        if not state.assistant_message:
            state.assistant_message = state.error_message or "流程执行过程中出现错误。"

        state.add_execution_record(
            step=WorkflowStep.ERROR.value,
            agent="System",
            success=False,
            message=state.assistant_message,
        )
        return state

    # =========================
    # 9) 通用执行模板
    # =========================

    def _execute_plan_step(
        self,
        state: WorkflowState,
        node_step: WorkflowStep,
        agent_name: str,
        agent: Any,
        success_status: WorkflowStatus,
        default_success_message: str,
    ) -> WorkflowState:
        """
        通用的 plan step 执行模板：

        正常路径：
        1. 标记当前 step 为 running
        2. 调 agent.run(state)
        3. 若 agent 没有显式打断流程，则：
           - 标记当前 step done
           - 推进 current_step_index
           - 从 plan 推导 next_step

        特殊路径：
        - 若 agent 将 next_step 显式设为 AWAIT_USER_INPUT / ERROR / SUPERVISOR
          则认为它触发了中断/异常/重规划，保留其覆盖结果
        """
        state.mark_current_plan_step_running()

        try:
            state = agent.run(state)
        except Exception as e:
            state.mark_current_plan_step_failed()
            return self._mark_node_error(
                state=state,
                node_step=node_step,
                agent_name=agent_name,
                message=f"{agent_name} 执行异常: {type(e).__name__}: {str(e)}",
            )

        # 特殊路径：等待用户补充信息
        if state.next_step == WorkflowStep.AWAIT_USER_INPUT:
            state.status = WorkflowStatus.NEEDS_USER_INPUT
            state.assistant_message = state.assistant_message or "需要你补充更多信息，才能继续执行。"
            state.add_execution_record(
                step=node_step.value,
                agent=agent_name,
                success=True,
                message=state.assistant_message,
                metadata={"interrupted_to": WorkflowStep.AWAIT_USER_INPUT.value},
            )
            return state

        # 特殊路径：agent 主动要求重规划
        if state.next_step == WorkflowStep.SUPERVISOR:
            state.status = WorkflowStatus.READY_FOR_EXECUTION
            state.assistant_message = state.assistant_message or "当前步骤执行后需要重新规划，正在返回 supervisor。"
            state.add_execution_record(
                step=node_step.value,
                agent=agent_name,
                success=True,
                message=state.assistant_message,
                metadata={"interrupted_to": WorkflowStep.SUPERVISOR.value},
            )
            return state

        # 特殊路径：agent 主动报错
        if state.next_step == WorkflowStep.ERROR or state.has_error:
            state.mark_current_plan_step_failed()
            if not state.error_message:
                state.error_message = f"{agent_name} 执行失败。"
            state.status = WorkflowStatus.ERROR
            state.assistant_message = state.assistant_message or state.error_message
            state.add_execution_record(
                step=node_step.value,
                agent=agent_name,
                success=False,
                message=state.assistant_message,
            )
            return state

        # 正常路径：按 plan 推进
        state.mark_current_plan_step_done()
        state.advance_plan_step()
        state.set_next_step_from_plan()
        state.status = success_status
        state.assistant_message = state.assistant_message or default_success_message

        state.add_execution_record(
            step=node_step.value,
            agent=agent_name,
            success=True,
            message=state.assistant_message,
            metadata={
                "current_step_index": state.current_step_index,
                "next_step": state.next_step.value if state.next_step else None,
            },
        )
        return state

    # =========================
    # 10) 校验与错误处理
    # =========================

    def _validate_current_plan_step(self, state: WorkflowState, expected_agent: str) -> bool:
        """
        校验当前 plan cursor 指向的步骤是否属于期望 agent。
        """
        current_step = state.get_current_plan_step()
        if current_step is None:
            return False
        return current_step.agent == expected_agent

    def _mark_node_error(
        self,
        state: WorkflowState,
        node_step: WorkflowStep,
        agent_name: str,
        message: str,
    ) -> WorkflowState:
        """
        节点统一错误处理。
        """
        state.has_error = True
        state.error_message = message
        state.status = WorkflowStatus.ERROR
        state.current_stage = WorkflowStep.ERROR
        state.next_step = WorkflowStep.ERROR
        state.is_finished = False
        state.assistant_message = message

        # 当前计划步骤若存在，标记失败
        try:
            state.mark_current_plan_step_failed()
        except Exception:
            pass

        state.add_execution_record(
            step=node_step.value,
            agent=agent_name,
            success=False,
            message=message,
        )
        return state