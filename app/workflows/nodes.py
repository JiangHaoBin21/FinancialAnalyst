"""LangGraph 节点实现。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.exc import MultipleResultsFound

from app.exceptions.data_exception import CompanyNotFoundError
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_COMPANY_PROFILE,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    DataPartResult,
    PlanStepStatus,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    complete_current_plan_step,
    error_update,
    execution_record,
    fail_current_plan_step,
    is_current_plan_agent,
    update_current_plan_step_status,
)
from collections import defaultdict


class WorkflowNodes:
    """供 LangGraph 构建器注册的节点集合。"""

    def __init__(
        self,
        supervisor_agent: Any,
        data_agent: Optional[Any] = None,
        analysis_agent: Optional[Any] = None,
        report_agent: Optional[Any] = None,
        reflection_agent: Optional[Any] = None,
        company_profile_fetch_skill: Optional[Any] = None,
        data_preparation_skill: Optional[Any] = None,
        completeness_checker_skill: Optional[Any] = None,
        backfill_plan_skill: Optional[Any] = None,
    ):
        self.supervisor_agent = supervisor_agent
        self.data_agent = data_agent
        self.analysis_agent = analysis_agent
        self.report_agent = report_agent
        self.reflection_agent = reflection_agent
        self.company_profile_fetch_skill = company_profile_fetch_skill
        self.data_preparation_skill = data_preparation_skill
        self.completeness_checker_skill = completeness_checker_skill
        self.backfill_plan_skill = backfill_plan_skill

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
            "current_stage": WorkflowStep.AWAIT_USER_INPUT,
            "status": WorkflowStatus.NEEDS_USER_INPUT,
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

    def data_planner_node(self, state: WorkflowState) -> dict:
        """运行 DataAgent，规划后续需要并行抓取的数据分片。"""
        if self.data_agent is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="DataAgent is not configured.",
            )

        if not is_current_plan_agent(state, "DataAgent"):
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="Current plan step does not match DataAgent.",
            )

        try:
            update = self.data_agent.run(state)
        except Exception as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(exc).__name__}: {exc}",
            )

        required_parts = list(update.get("required_data_parts", []))
        message = update.get("assistant_message") or "DataAgent planned data requirements."
        return {
            **update,
            "current_stage": WorkflowStep.DATA,
            "status": WorkflowStatus.DATA_PLANNED,
            "task_plan": update_current_plan_step_status(state, PlanStepStatus.RUNNING),
            "data_part_results": [],
            "data_fetch_errors": [],
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataAgent",
                    success=True,
                    message=message,
                    metadata={"required_data_parts": required_parts},
                )
            ],
        }

    def prepare_company_context_node(self, state: WorkflowState) -> dict:
        """抓取公司基础画像数据。"""
        print("[DataNode] 解析公司ts_code和公司名...")
        company_name = state.get("company_name")
        ts_code = state.get("ts_code")
        try:
            company_profile = self.company_profile_fetch_skill.fetch(company_name, ts_code)
        except MultipleResultsFound as e:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(e).__name__}: {e}",
            )
        except CompanyNotFoundError as e:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(e).__name__}: {e}",
            )
        return {
            "ts_code": company_profile["ts_code"],
            "company_name": company_profile["name"],
            "company_profile": company_profile
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
    # 并行数据抓取节点
    # =========================

    def fetch_income_statement_node(self, state: WorkflowState) -> dict:
        """抓取利润表数据。"""
        if state.get("need_backfill"):
            print("[DataNode][TuShare回源] 回源拉取利润表数据并落库...")
        else:
            print("[DataNode] 检索利润表数据表...")
        payload = self.data_preparation_skill.prepare(
            time_range=state.get("time_range"),
            required_parts=[DATA_PART_INCOME],
            company_profile=state.get("company_profile"),
            backfill=state.get("need_backfill"),
        )
        return self._data_part_update(DATA_PART_INCOME, payload)

    def fetch_balance_sheet_node(self, state: WorkflowState) -> dict:
        """抓取资产负债表数据。"""
        if state.get("need_backfill"):
            print("[DataNode][TuShare回源] 回源拉取资产负债表数据并落库...")
        else:
            print("[DataNode] 检索资产负债表数据表...")
        payload = self.data_preparation_skill.prepare(
            time_range=state.get("time_range"),
            required_parts=[DATA_PART_BALANCE],
            company_profile=state.get("company_profile"),
            backfill=state.get("need_backfill"),
        )
        return self._data_part_update(DATA_PART_BALANCE, payload)

    def fetch_cashflow_statement_node(self, state: WorkflowState) -> dict:
        """抓取现金流量表数据。"""
        if state.get("need_backfill"):
            print("[DataNode][TuShare回源] 回源拉取现金流量表数据并落库...")
        else:
            print("[DataNode] 检索现金流量表数据表...")
        payload = self.data_preparation_skill.prepare(
            time_range=state.get("time_range"),
            required_parts=[DATA_PART_CASHFLOW],
            company_profile=state.get("company_profile"),
            backfill=state.get("need_backfill"),
        )
        return self._data_part_update(DATA_PART_CASHFLOW, payload)

    def fetch_financial_indicator_node(self, state: WorkflowState) -> dict:
        """抓取核心财务指标数据。"""
        if state.get("need_backfill"):
            print("[DataNode][TuShare回源] 回源拉取核心财务指标数据并落库...")
        else:
            print("[DataNode] 检索核心财务指标数据表...")
        payload = self.data_preparation_skill.prepare(
            time_range=state.get("time_range"),
            required_parts=[DATA_PART_INDICATORS],
            company_profile=state.get("company_profile"),
            backfill=state.get("need_backfill"),
        )
        return self._data_part_update(DATA_PART_INDICATORS, payload)

    def data_merge_node(self, state: WorkflowState) -> dict:
        """校验并合并所有并行数据抓取节点的结果。"""
        print("[DataNode] 并行节点数据结果合并...")
        required_parts = state.get("required_data_parts", [])
        results = state.get("data_part_results", [])

        financial_data = defaultdict(list)
        for result in results:
            financial_data[result.part_name].append(result.payload)

        return {
            "financial_data": financial_data,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:merge node",
                    success=True,
                    message="合并并行数据结果",
                    metadata={"part_name": "all"},
                )
            ]
        }

        # plan_update = complete_current_plan_step(state)
        # return {
        #     **plan_update,
        #     "current_stage": WorkflowStep.DATA,
        #     "status": WorkflowStatus.DATA_READY,
        #     "company_profile": company_profile,
        #     "financial_data": financial_data,
        #     "data_summary": data_summary,
        #     "assistant_message": "Data stage completed with parallel fetch nodes.",
        #     "execution_history": [
        #         execution_record(
        #             step=WorkflowStep.DATA.value,
        #             agent="DataMerge",
        #             success=True,
        #             message="Merged parallel data results.",
        #             metadata={
        #                 "required_parts": sorted(required_parts),
        #                 "fetched_parts": sorted(result_by_part),
        #                 "next_step": _enum_value(plan_update.get("next_step")),
        #             },
        #         )
        #     ],
        # }

    def completeness_check_node(self, state: WorkflowState) -> dict:
        """执行完整性检查阶段的计划步骤。"""
        print("[DataNode] 检查合并后数据是否完整...")
        completeness_check_result = self.company_profile_fetch_skill.skill_check(
            requested_time_range=state.get("time_range"),
            financial_data=state.get("financial_data"),
            required_parts=state.get("required_data_parts")
        )
        return {
            "completeness_check_result": completeness_check_result,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:completeness check",
                    success=True,
                    message="数据完整性检查"
                )
            ]
        }

    def backfill_planner_node(self, state: WorkflowState) -> dict:
        """执行回源计划步骤。"""
        if state.get("data_completeness_check_result")["has_missing_data"]:
            print("[DataNode] 数据有缺失，判定是否需要回源...")
            already_backfill = state.get("already_backfill") + 1
            if self.backfill_plan_skill.backfill_plan():
                print(f"[DataNode] 需要回源,当前已回源次数：{already_backfill}次...")




    # =========================
    # 终态节点
    # =========================

    def finish_node(self, state: WorkflowState) -> dict:
        """生成工作流完成状态。"""
        final_response = state.get("final_report") or state.get("final_response")
        message = state.get("assistant_message") or "Workflow finished."
        return {
            "current_stage": WorkflowStep.FINISHED,
            "status": WorkflowStatus.FINISHED,
            "next_step": WorkflowStep.FINISHED,
            "is_finished": True,
            "final_response": final_response,
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
        message = state.get("assistant_message") or state.get("error_message") or (
            "Workflow execution failed."
        )
        return {
            "current_stage": WorkflowStep.ERROR,
            "status": WorkflowStatus.ERROR,
            "next_step": WorkflowStep.ERROR,
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
        """执行一个受计划约束的 Agent 步骤，并统一处理跳转和错误。"""
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

        running_update = {
            "task_plan": update_current_plan_step_status(state, PlanStepStatus.RUNNING),
        }
        state_for_agent = {**state, **running_update}

        try:
            agent_update = agent.run(state_for_agent)
        except Exception as exc:
            return self._node_error(
                state=state,
                node_step=node_step,
                agent_name=expected_agent,
                message=f"{expected_agent} failed: {type(exc).__name__}: {exc}",
            )

        merged = {**state_for_agent, **agent_update}
        # Agent 可以主动请求补充信息，此时工作流暂停到等待用户输入节点。
        if merged.get("next_step") == WorkflowStep.AWAIT_USER_INPUT:
            return {
                **agent_update,
                "status": WorkflowStatus.NEEDS_USER_INPUT,
                "current_stage": node_step,
                "execution_history": [
                    execution_record(
                        step=node_step.value,
                        agent=expected_agent,
                        success=True,
                        message=merged.get("assistant_message") or "Needs user input.",
                        metadata={"interrupted_to": WorkflowStep.AWAIT_USER_INPUT.value},
                    )
                ],
            }

        # Agent 可以要求回到 Supervisor 重新规划后续步骤。
        if merged.get("next_step") == WorkflowStep.SUPERVISOR:
            return {
                **agent_update,
                "status": WorkflowStatus.READY_FOR_EXECUTION,
                "current_stage": node_step,
                "execution_history": [
                    execution_record(
                        step=node_step.value,
                        agent=expected_agent,
                        success=True,
                        message=merged.get("assistant_message") or "Replanning requested.",
                        metadata={"interrupted_to": WorkflowStep.SUPERVISOR.value},
                    )
                ],
            }

        # 错误状态会标记当前计划步骤失败，并交给错误节点收尾。
        if merged.get("next_step") == WorkflowStep.ERROR or merged.get("has_error"):
            update = {
                **agent_update,
                **fail_current_plan_step(state),
                "status": WorkflowStatus.ERROR,
                "current_stage": WorkflowStep.ERROR,
                "next_step": WorkflowStep.ERROR,
                "has_error": True,
                "error_message": merged.get("error_message") or f"{expected_agent} failed.",
            }
            return {
                **update,
                "execution_history": [
                    execution_record(
                        step=node_step.value,
                        agent=expected_agent,
                        success=False,
                        message=update["error_message"],
                    )
                ],
            }

        # 正常完成时推进计划索引，并把 next_step 指向下一类节点。
        plan_update = complete_current_plan_step(state_for_agent)
        message = agent_update.get("assistant_message") or default_success_message
        return {
            **agent_update,
            **plan_update,
            "current_stage": node_step,
            "status": success_status,
            "assistant_message": message,
            "execution_history": [
                execution_record(
                    step=node_step.value,
                    agent=expected_agent,
                    success=True,
                    message=message,
                    metadata={
                        "current_step_index": plan_update.get("current_step_index"),
                        "next_step": _enum_value(plan_update.get("next_step")),
                    },
                )
            ],
        }

    @staticmethod
    def _data_part_update(part_name: str, payload: Any) -> dict:
        """把单个数据分片结果包装成 LangGraph 可合并的局部更新。"""
        return {
            "data_part_results": [
                DataPartResult(
                    part_name=part_name,
                    payload=payload,
                    success=True,
                    message=f"Fetched {part_name}.",
                )
            ],
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent=f"DataNode:{part_name}",
                    success=True,
                    message=f"Fetched {part_name}.",
                    metadata={"part_name": part_name},
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


def _payload_count(payload: Any) -> int:
    """估算数据载荷中的记录数量，用于数据汇总元信息。"""
    if isinstance(payload, dict):
        lengths = [len(value) for value in payload.values() if isinstance(value, list)]
        return max(lengths) if lengths else len(payload)
    if isinstance(payload, list):
        return len(payload)
    return 1 if payload else 0
