"""Workflow graph / orchestrator.

职责：
1. 作为整个多 Agent 财报分析工作流的统一调度器
2. 根据 state.next_step 路由到对应 node
3. 控制执行循环，直到 finished / await_user_input / error
4. 提供：
   - run(user_query): 从用户请求启动一次完整工作流
   - continue_from_state(state): 从已有状态继续执行
   - resume_with_user_input(state, user_input): 用户补充信息后继续执行
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Optional

from app.workflows.state import WorkflowState, WorkflowStep, WorkflowStatus
from app.workflows.nodes import WorkflowNodes


class WorkflowGraph:
    """
    多 Agent 财报分析系统的 graph / orchestrator。

    设计原则：
    1. graph 只负责“调度”，不负责具体业务
    2. 正常主流程依赖 state.next_step 路由
    3. node 层负责具体执行和 state 写回
    4. graph 负责循环推进，直到：
       - FINISHED
       - AWAIT_USER_INPUT
       - ERROR
    """

    def __init__(
        self,
        nodes: WorkflowNodes,
        max_iterations: int = 5,
        enable_trace: bool = False,
    ):
        self.nodes = nodes
        self.max_iterations = max_iterations
        self.enable_trace = enable_trace

        self._route_table: dict[WorkflowStep, Callable[[WorkflowState], WorkflowState]] = {
            WorkflowStep.SUPERVISOR: self.nodes.supervisor_node,
            WorkflowStep.AWAIT_USER_INPUT: self.nodes.await_user_input_node,
            WorkflowStep.DATA: self.nodes.data_node,
            WorkflowStep.ANALYSIS: self.nodes.analysis_node,
            WorkflowStep.REPORT: self.nodes.report_node,
            WorkflowStep.REFLECTION: self.nodes.reflection_node,
            WorkflowStep.FINISHED: self.nodes.finish_node,
            WorkflowStep.ERROR: self.nodes.error_node,
        }

    # =========================
    # 1) 对外主入口
    # =========================

    def run(self, user_query: str) -> WorkflowState:
        """
        从用户输入直接启动一次完整工作流。
        """
        state = WorkflowState(user_query=user_query)
        state.next_step = WorkflowStep.SUPERVISOR
        return self.continue_from_state(state)

    def continue_from_state(self, state: WorkflowState) -> WorkflowState:
        """
        从一个已有 state 继续推进工作流。
        适用场景：
        - supervisor 刚写好计划后继续执行
        - 某一步执行完后继续推进
        - 从持久化状态恢复执行
        """
        if not isinstance(state, WorkflowState):
            raise TypeError("continue_from_state 需要传入 WorkflowState 实例。")

        # 若 next_step 为空，给一个合理入口
        if state.next_step is None:
            state.next_step = self._infer_entry_step(state)

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            current_route = state.next_step
            if current_route is None:
                state.set_error("graph 无法继续执行：state.next_step 为空。")
                state = self.nodes.error_node(state)
                break

            if self.enable_trace:
                self._trace(
                    state=state,
                    prefix=f"[graph] iteration={iteration}",
                )

            node_fn = self._route_table.get(current_route)
            if node_fn is None:
                state.set_error(f"graph 路由失败：未找到 {current_route.value} 对应节点。")
                state = self.nodes.error_node(state)
                break

            prev_stage = state.current_stage
            prev_next_step = state.next_step
            prev_history_len = len(state.execution_history)

            state = node_fn(state)

            if self.enable_trace:
                self._trace_after_node(
                    prev_stage=prev_stage,
                    prev_next_step=prev_next_step,
                    prev_history_len=prev_history_len,
                    state=state,
                )

            # ---- 停机条件 1：完成 ----
            if state.current_stage == WorkflowStep.FINISHED or state.is_finished:
                # 保守兜底：确保 finish_node 至少被执行一次
                if state.current_stage != WorkflowStep.FINISHED:
                    state = self.nodes.finish_node(state)
                break

            # ---- 停机条件 2：等待用户输入 ----
            if state.next_step == WorkflowStep.AWAIT_USER_INPUT or state.status == WorkflowStatus.NEEDS_USER_INPUT:
                # 确保 await_user_input_node 被执行一次，用于统一写 execution_history
                if state.current_stage != WorkflowStep.AWAIT_USER_INPUT:
                    state = self.nodes.await_user_input_node(state)
                break

            # ---- 停机条件 3：错误 ----
            if state.next_step == WorkflowStep.ERROR or state.has_error or state.status == WorkflowStatus.ERROR:
                # 确保 error_node 被执行一次，用于统一收敛
                if state.current_stage != WorkflowStep.ERROR:
                    state = self.nodes.error_node(state)
                break

            # ---- 防御性检查：node 执行后没有给出新的 next_step ----
            if state.next_step is None:
                state.set_error("graph 检测到节点执行后未写回 next_step，流程无法继续。")
                state = self.nodes.error_node(state)
                break

        else:
            # while 正常耗尽 max_iterations
            state.set_error(
                f"graph 执行超过最大迭代次数 {self.max_iterations}，疑似出现死循环。"
            )
            state = self.nodes.error_node(state)

        return state

    def resume_with_user_input(self, state: WorkflowState, user_input: str) -> WorkflowState:
        """
        当工作流处于 AWAIT_USER_INPUT 时，用户补充信息后继续执行。

        当前这版最稳的策略：
        - 将 user_input 直接并入原始 user_query
        - 回到 supervisor 重新规划
        """
        if not isinstance(state, WorkflowState):
            raise TypeError("resume_with_user_input 需要传入 WorkflowState 实例。")

        normalized_input = (user_input or "").strip()
        if not normalized_input:
            state.status = WorkflowStatus.NEEDS_USER_INPUT
            state.next_step = WorkflowStep.AWAIT_USER_INPUT
            state.assistant_message = "你还没有补充有效信息，请继续告诉我缺失的内容。"
            return state

        original_query = (state.user_query or "").strip()
        if original_query:
            state.user_query = f"{original_query}\n\n补充信息：{normalized_input}"
        else:
            state.user_query = normalized_input

        # 清理“等待输入”状态，并回到 supervisor 重规划
        state.needs_user_input = False
        state.missing_fields = []
        state.assistant_message = None
        state.has_error = False
        state.error_message = None
        state.current_stage = WorkflowStep.SUPERVISOR
        state.next_step = WorkflowStep.SUPERVISOR
        state.status = WorkflowStatus.INIT
        state.is_finished = False

        return self.continue_from_state(state)

    # =========================
    # 2) 单步执行（调试很有用）
    # =========================

    def step_once(self, state: WorkflowState) -> WorkflowState:
        """
        只执行一个 node，适合调试和单测。
        """
        if not isinstance(state, WorkflowState):
            raise TypeError("step_once 需要传入 WorkflowState 实例。")

        if state.next_step is None:
            state.next_step = self._infer_entry_step(state)

        node_fn = self._route_table.get(state.next_step)
        if node_fn is None:
            state.set_error(f"graph 路由失败：未找到 {state.next_step.value} 对应节点。")
            return self.nodes.error_node(state)

        return node_fn(state)

    # =========================
    # 3) 内部辅助方法
    # =========================

    def _infer_entry_step(self, state: WorkflowState) -> WorkflowStep:
        """
        当外部没有显式提供 next_step 时，graph 推断一个合理入口。

        推断规则：
        1. needs_user_input / NEEDS_USER_INPUT -> AWAIT_USER_INPUT
        2. has_error / ERROR -> ERROR
        3. is_finished / FINISHED -> FINISHED
        4. 有 task_plan -> 按 plan 推导 next_step
        5. 其他情况 -> SUPERVISOR
        """
        if state.has_error or state.status == WorkflowStatus.ERROR:
            return WorkflowStep.ERROR

        if state.is_finished or state.status == WorkflowStatus.FINISHED:
            return WorkflowStep.FINISHED

        if state.needs_user_input or state.status == WorkflowStatus.NEEDS_USER_INPUT:
            return WorkflowStep.AWAIT_USER_INPUT

        if state.task_plan:
            state.set_next_step_from_plan()
            return state.next_step or WorkflowStep.ERROR

        return WorkflowStep.SUPERVISOR

    def _trace(self, state: WorkflowState, prefix: str = "[graph]") -> None:
        """
        调试打印：执行前。
        """
        plan_step = state.get_current_plan_step()
        plan_step_desc = None
        if plan_step is not None:
            plan_step_desc = {
                "step_id": plan_step.step_id,
                "agent": plan_step.agent,
                "action": plan_step.action,
                "status": plan_step.status.value if hasattr(plan_step.status, "value") else str(plan_step.status),
            }

        print(
            f"{prefix} "
            f"current_stage={getattr(state.current_stage, 'value', state.current_stage)} | "
            f"next_step={getattr(state.next_step, 'value', state.next_step)} | "
            f"status={getattr(state.status, 'value', state.status)} | "
            f"step_index={state.current_step_index} | "
            f"plan_step={plan_step_desc}"
        )

    def _trace_after_node(
        self,
        prev_stage: WorkflowStep,
        prev_next_step: WorkflowStep,
        prev_history_len: int,
        state: WorkflowState,
    ) -> None:
        """
        调试打印：执行后。
        """
        latest_record = None
        if len(state.execution_history) > prev_history_len:
            latest_record = state.execution_history[-1]

        latest_record_view = None
        if latest_record is not None:
            latest_record_view = {
                "step": latest_record.step,
                "agent": latest_record.agent,
                "success": latest_record.success,
                "message": latest_record.message,
                "metadata": latest_record.metadata,
            }

        print(
            "[graph.after] "
            f"prev_stage={getattr(prev_stage, 'value', prev_stage)} | "
            f"prev_next_step={getattr(prev_next_step, 'value', prev_next_step)} | "
            f"current_stage={getattr(state.current_stage, 'value', state.current_stage)} | "
            f"next_step={getattr(state.next_step, 'value', state.next_step)} | "
            f"status={getattr(state.status, 'value', state.status)} | "
            f"is_finished={state.is_finished} | "
            f"has_error={state.has_error} | "
            f"latest_record={latest_record_view}"
        )

    # =========================
    # 4) 可选：便于前端/接口层读取
    # =========================

    @staticmethod
    def state_to_dict(state: WorkflowState) -> dict[str, Any]:
        """
        将 WorkflowState 转成适合接口返回的 dict。
        dataclass 内嵌 Enum 时做一层轻量归一化。
        """
        if not is_dataclass(state):
            raise TypeError("state_to_dict 需要传入 dataclass 实例。")

        raw = asdict(state)
        return WorkflowGraph._normalize_for_json(raw)

    @staticmethod
    def _normalize_for_json(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: WorkflowGraph._normalize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [WorkflowGraph._normalize_for_json(v) for v in obj]
        if hasattr(obj, "value"):
            return obj.value
        return obj