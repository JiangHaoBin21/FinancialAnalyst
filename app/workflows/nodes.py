"""LangGraph node implementations."""

from __future__ import annotations

from typing import Any, Optional

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


class WorkflowNodes:
    """Node collection used by the LangGraph builder."""

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
    # Agent-level nodes
    # =========================

    def supervisor_node(self, state: WorkflowState) -> dict:
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

    def analysis_node(self, state: WorkflowState) -> dict:
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.ANALYSIS,
            expected_agent="AnalysisAgent",
            agent=self.analysis_agent,
            success_status=WorkflowStatus.ANALYSIS_READY,
            default_success_message="AnalysisAgent completed analysis.",
        )

    def report_node(self, state: WorkflowState) -> dict:
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.REPORT,
            expected_agent="ReportAgent",
            agent=self.report_agent,
            success_status=WorkflowStatus.REPORT_READY,
            default_success_message="ReportAgent generated report.",
        )

    def reflection_node(self, state: WorkflowState) -> dict:
        return self._execute_agent_plan_step(
            state=state,
            node_step=WorkflowStep.REFLECTION,
            expected_agent="ReflectionAgent",
            agent=self.reflection_agent,
            success_status=WorkflowStatus.REFLECTION_DONE,
            default_success_message="ReflectionAgent completed review.",
        )

    # =========================
    # Parallel data fetch nodes
    # =========================

    def fetch_company_profile_node(self, state: WorkflowState) -> dict:
        print("[DataNode] fetch_company_profile...")
        company_name = state.get("company_name") or "MockCompany"
        ts_code = state.get("ts_code") or "000001.SZ"
        payload = {
            "company_name": company_name,
            "ts_code": ts_code,
            "industry": "Mock Industry",
        }
        return self._data_part_update(DATA_PART_COMPANY_PROFILE, payload)

    def fetch_income_statement_node(self, state: WorkflowState) -> dict:
        print("[DataNode] fetch_income_statement...")
        payload = {
            "revenue": [100, 120, 150],
            "net_profit": [20, 25, 32],
        }
        return self._data_part_update(DATA_PART_INCOME, payload)

    def fetch_balance_sheet_node(self, state: WorkflowState) -> dict:
        print("[DataNode] fetch_balance_sheet...")
        payload = {
            "assets": [200, 230, 260],
            "liabilities": [80, 90, 100],
        }
        return self._data_part_update(DATA_PART_BALANCE, payload)

    def fetch_cashflow_statement_node(self, state: WorkflowState) -> dict:
        print("[DataNode] fetch_cashflow_statement...")
        payload = {
            "operating_cashflow": [18, 26, 35],
            "free_cashflow": [10, 16, 22],
        }
        return self._data_part_update(DATA_PART_CASHFLOW, payload)

    def fetch_financial_indicator_node(self, state: WorkflowState) -> dict:
        print("[DataNode] fetch_financial_indicator...")
        payload = {
            "gross_margin": [0.28, 0.30, 0.32],
            "net_margin": [0.20, 0.21, 0.213],
            "debt_to_asset": [0.40, 0.391, 0.385],
        }
        return self._data_part_update(DATA_PART_INDICATORS, payload)

    def data_merge_node(self, state: WorkflowState) -> dict:
        required_parts = set(state.get("required_data_parts", []))
        results = state.get("data_part_results", [])
        result_by_part = {
            result.part_name: result
            for result in results
            if result.success
        }

        missing_parts = sorted(required_parts - set(result_by_part))
        if missing_parts:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataMerge",
                message="Missing data parts: " + ", ".join(missing_parts),
            )

        company_profile = (
            result_by_part.get(DATA_PART_COMPANY_PROFILE, DataPartResult(DATA_PART_COMPANY_PROFILE, {})).payload
        )
        financial_data = {
            part_name: result.payload
            for part_name, result in result_by_part.items()
            if part_name != DATA_PART_COMPANY_PROFILE
        }
        data_summary = {
            "message": "Financial data prepared by parallel LangGraph data nodes.",
            "required_parts": sorted(required_parts),
            "fetched_parts": sorted(result_by_part),
            "record_counts": {
                part_name: _payload_count(result.payload)
                for part_name, result in result_by_part.items()
            },
        }

        plan_update = complete_current_plan_step(state)
        return {
            **plan_update,
            "current_stage": WorkflowStep.DATA,
            "status": WorkflowStatus.DATA_READY,
            "company_profile": company_profile,
            "financial_data": financial_data,
            "data_summary": data_summary,
            "assistant_message": "Data stage completed with parallel fetch nodes.",
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataMerge",
                    success=True,
                    message="Merged parallel data results.",
                    metadata={
                        "required_parts": sorted(required_parts),
                        "fetched_parts": sorted(result_by_part),
                        "next_step": _enum_value(plan_update.get("next_step")),
                    },
                )
            ],
        }

    # =========================
    # Terminal nodes
    # =========================

    def finish_node(self, state: WorkflowState) -> dict:
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
    # Internal helpers
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
    return value.value if hasattr(value, "value") else value


def _payload_count(payload: Any) -> int:
    if isinstance(payload, dict):
        lengths = [len(value) for value in payload.values() if isinstance(value, list)]
        return max(lengths) if lengths else len(payload)
    if isinstance(payload, list):
        return len(payload)
    return 1 if payload else 0
