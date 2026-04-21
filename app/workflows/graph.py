"""LangGraph-native workflow orchestration with parallel data fan-out."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.workflows.nodes import WorkflowNodes
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_COMPANY_PROFILE,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    create_initial_state,
    error_update,
    normalize_for_json,
    next_workflow_step,
)


class WorkflowGraph:
    """Public workflow facade backed directly by LangGraph state."""

    def __init__(
        self,
        nodes: WorkflowNodes,
        max_iterations: int = 20,
        enable_trace: bool = False,
    ):
        self.nodes = nodes
        self.max_iterations = max_iterations
        self.enable_trace = enable_trace
        self._route_table: dict[WorkflowStep, Callable[[WorkflowState], dict]] = {
            WorkflowStep.SUPERVISOR: self.nodes.supervisor_node,
            WorkflowStep.AWAIT_USER_INPUT: self.nodes.await_user_input_node,
            WorkflowStep.DATA: self.nodes.data_planner_node,
            WorkflowStep.ANALYSIS: self.nodes.analysis_node,
            WorkflowStep.REPORT: self.nodes.report_node,
            WorkflowStep.REFLECTION: self.nodes.reflection_node,
            WorkflowStep.FINISHED: self.nodes.finish_node,
            WorkflowStep.ERROR: self.nodes.error_node,
        }
        self._compiled_graph = self._build_langgraph()

    def run(self, user_query: str) -> WorkflowState:
        """Start a workflow from a user query."""
        return self.continue_from_state(create_initial_state(user_query=user_query))

    def continue_from_state(self, state: WorkflowState) -> WorkflowState:
        """Continue execution from an existing LangGraph-native state dict."""
        if not isinstance(state, dict):
            raise TypeError("continue_from_state requires a WorkflowState dict.")

        if state.get("next_step") is None:
            state = {**state, "next_step": self._infer_entry_step(state)}

        try:
            return self._compiled_graph.invoke(
                state,
                config={"recursion_limit": self._recursion_limit},
            )
        except Exception as exc:
            failed_state = {
                **state,
                **error_update(f"LangGraph execution failed: {type(exc).__name__}: {exc}"),
            }
            return self._merge_state_update(failed_state, self.nodes.error_node(failed_state))

    def resume_with_user_input(self, state: WorkflowState, user_input: str) -> WorkflowState:
        """Resume a paused workflow after the user provides missing information."""
        if not isinstance(state, dict):
            raise TypeError("resume_with_user_input requires a WorkflowState dict.")

        normalized_input = (user_input or "").strip()
        if not normalized_input:
            return {
                **state,
                "status": WorkflowStatus.NEEDS_USER_INPUT,
                "next_step": WorkflowStep.AWAIT_USER_INPUT,
                "assistant_message": "你还没有补充有效信息，请继续告诉我缺失的内容。",
            }

        original_query = (state.get("user_query") or "").strip()
        if original_query:
            user_query = f"{original_query}\n\n补充信息：{normalized_input}"
        else:
            user_query = normalized_input

        resumed_state = {
            **state,
            "user_query": user_query,
            "needs_user_input": False,
            "missing_fields": [],
            "assistant_message": None,
            "has_error": False,
            "error_message": None,
            "current_stage": WorkflowStep.SUPERVISOR,
            "next_step": WorkflowStep.SUPERVISOR,
            "status": WorkflowStatus.INIT,
            "is_finished": False,
        }
        return self.continue_from_state(resumed_state)

    def step_once(self, state: WorkflowState) -> WorkflowState:
        """Execute a single node and merge its partial update into state."""
        if not isinstance(state, dict):
            raise TypeError("step_once requires a WorkflowState dict.")

        route = state.get("next_step") or self._infer_entry_step(state)
        node_fn = self._route_table.get(route)
        if node_fn is None:
            update = error_update(f"No workflow node found for route {_enum_value(route)}.")
            return self._merge_state_update(state, update)

        return self._merge_state_update(state, node_fn(state))

    @property
    def _recursion_limit(self) -> int:
        return max(self.max_iterations + 8, 16)

    def _build_langgraph(self):
        StateGraph, START, END = self._import_langgraph()

        builder = StateGraph(WorkflowState)

        builder.add_node("supervisor", self._wrap_node(self.nodes.supervisor_node))
        builder.add_node("await_user_input", self._wrap_node(self.nodes.await_user_input_node))
        builder.add_node("data_planner", self._wrap_node(self.nodes.data_planner_node))
        builder.add_node("fetch_company_profile", self._wrap_node(self.nodes.fetch_company_profile_node))
        builder.add_node("fetch_income_statement", self._wrap_node(self.nodes.fetch_income_statement_node))
        builder.add_node("fetch_balance_sheet", self._wrap_node(self.nodes.fetch_balance_sheet_node))
        builder.add_node("fetch_cashflow_statement", self._wrap_node(self.nodes.fetch_cashflow_statement_node))
        builder.add_node("fetch_financial_indicator", self._wrap_node(self.nodes.fetch_financial_indicator_node))
        builder.add_node("data_merge", self._wrap_node(self.nodes.data_merge_node))
        builder.add_node("analysis", self._wrap_node(self.nodes.analysis_node))
        builder.add_node("report", self._wrap_node(self.nodes.report_node))
        builder.add_node("reflection", self._wrap_node(self.nodes.reflection_node))
        builder.add_node("finished", self._wrap_node(self.nodes.finish_node))
        builder.add_node("error", self._wrap_node(self.nodes.error_node))

        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges("supervisor", self._route_after_node, self._route_path_map(END))
        builder.add_conditional_edges("data_planner", self._route_data_parts, self._data_route_path_map())

        for fetch_node in (
            "fetch_company_profile",
            "fetch_income_statement",
            "fetch_balance_sheet",
            "fetch_cashflow_statement",
            "fetch_financial_indicator",
        ):
            builder.add_edge(fetch_node, "data_merge")

        builder.add_conditional_edges("data_merge", self._route_after_node, self._route_path_map(END))
        for node_name in ("analysis", "report", "reflection"):
            builder.add_conditional_edges(node_name, self._route_after_node, self._route_path_map(END))

        builder.add_edge("await_user_input", END)
        builder.add_edge("finished", END)
        builder.add_edge("error", END)

        return builder.compile()

    @staticmethod
    def _import_langgraph():
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise ImportError(
                "LangGraph is required for WorkflowGraph. Install it with "
                "`pip install langgraph` or add it to your project dependencies."
            ) from exc
        return StateGraph, START, END

    @staticmethod
    def _route_path_map(end_marker: str) -> dict[str, str]:
        return {
            "await_user_input": "await_user_input",
            "data": "data_planner",
            "analysis": "analysis",
            "report": "report",
            "reflection": "reflection",
            "finished": "finished",
            "error": "error",
            "end": end_marker,
        }

    @staticmethod
    def _data_route_path_map() -> dict[str, str]:
        return {
            DATA_PART_COMPANY_PROFILE: "fetch_company_profile",
            DATA_PART_INCOME: "fetch_income_statement",
            DATA_PART_BALANCE: "fetch_balance_sheet",
            DATA_PART_CASHFLOW: "fetch_cashflow_statement",
            DATA_PART_INDICATORS: "fetch_financial_indicator",
            "data_merge": "data_merge",
            "error": "error",
        }

    def _wrap_node(self, node_fn: Callable[[WorkflowState], dict]) -> Callable[[WorkflowState], dict]:
        def wrapped(state: WorkflowState) -> dict:
            if self.enable_trace:
                self._trace(state, prefix=f"[langgraph.before:{node_fn.__name__}]")

            update = node_fn(state)

            if self.enable_trace:
                preview_state = self._merge_state_update(state, update)
                self._trace(preview_state, prefix=f"[langgraph.after:{node_fn.__name__}]")

            return update

        return wrapped

    def _route_after_node(self, state: WorkflowState) -> str:
        if state.get("current_stage") == WorkflowStep.FINISHED or state.get("is_finished"):
            return "end" if state.get("current_stage") == WorkflowStep.FINISHED else "finished"

        if state.get("next_step") == WorkflowStep.AWAIT_USER_INPUT or state.get("status") == WorkflowStatus.NEEDS_USER_INPUT:
            return "end" if state.get("current_stage") == WorkflowStep.AWAIT_USER_INPUT else "await_user_input"

        if state.get("next_step") == WorkflowStep.ERROR or state.get("has_error") or state.get("status") == WorkflowStatus.ERROR:
            return "end" if state.get("current_stage") == WorkflowStep.ERROR else "error"

        next_step = state.get("next_step")
        if next_step == WorkflowStep.DATA:
            return "data"
        if next_step == WorkflowStep.ANALYSIS:
            return "analysis"
        if next_step == WorkflowStep.REPORT:
            return "report"
        if next_step == WorkflowStep.REFLECTION:
            return "reflection"
        if next_step == WorkflowStep.FINISHED:
            return "finished"

        return "error"

    @staticmethod
    def _route_data_parts(state: WorkflowState) -> list[str]:
        if state.get("has_error") or state.get("status") == WorkflowStatus.ERROR:
            return ["error"]

        routes = [
            part
            for part in state.get("required_data_parts", [])
            if part in {
                DATA_PART_COMPANY_PROFILE,
                DATA_PART_INCOME,
                DATA_PART_BALANCE,
                DATA_PART_CASHFLOW,
                DATA_PART_INDICATORS,
            }
        ]
        return routes or ["data_merge"]

    @staticmethod
    def _infer_entry_step(state: WorkflowState) -> WorkflowStep:
        if state.get("has_error") or state.get("status") == WorkflowStatus.ERROR:
            return WorkflowStep.ERROR
        if state.get("is_finished") or state.get("status") == WorkflowStatus.FINISHED:
            return WorkflowStep.FINISHED
        if state.get("needs_user_input") or state.get("status") == WorkflowStatus.NEEDS_USER_INPUT:
            return WorkflowStep.AWAIT_USER_INPUT
        if state.get("task_plan"):
            return next_workflow_step(
                state.get("task_plan", []),
                state.get("current_step_index", 0),
            )
        return WorkflowStep.SUPERVISOR

    @staticmethod
    def _merge_state_update(state: WorkflowState, update: dict) -> WorkflowState:
        merged = dict(state)
        for key, value in update.items():
            if key in {"execution_history", "data_part_results", "data_fetch_errors"}:
                merged[key] = list(merged.get(key, [])) + list(value or [])
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _trace(state: WorkflowState, prefix: str) -> None:
        print(
            f"{prefix} "
            f"stage={_enum_value(state.get('current_stage'))} | "
            f"next={_enum_value(state.get('next_step'))} | "
            f"status={_enum_value(state.get('status'))} | "
            f"step_index={state.get('current_step_index')} | "
            f"required_parts={state.get('required_data_parts', [])}"
        )

    @staticmethod
    def state_to_dict(state: WorkflowState) -> dict[str, Any]:
        """Convert WorkflowState into a JSON-friendly dictionary."""
        return normalize_for_json(dict(state))


def build_workflow_graph(
    *,
    llm_client: Optional[Any] = None,
    nodes: Optional[WorkflowNodes] = None,
    max_iterations: int = 20,
    enable_trace: bool = False,
) -> WorkflowGraph:
    """Build the default LangGraph-native workflow graph."""
    if nodes is None:
        from app.agents.analysis_agent import AnalysisAgent
        from app.agents.data_agent import DataAgent
        from app.agents.reflection_agent import ReflectionAgent
        from app.agents.report_agent import ReportAgent
        from app.agents.supervisor_agent import SupervisorAgent
        from app.llms.openai_client import OpenAIClient
        from app.skills.planning.planning_skill import PlanningSkill

        llm_client = llm_client or OpenAIClient()
        planning_skill = PlanningSkill(llm_client=llm_client)
        nodes = WorkflowNodes(
            supervisor_agent=SupervisorAgent(planning_skill=planning_skill),
            data_agent=DataAgent(),
            analysis_agent=AnalysisAgent(),
            report_agent=ReportAgent(),
            reflection_agent=ReflectionAgent(),
        )

    return WorkflowGraph(
        nodes=nodes,
        max_iterations=max_iterations,
        enable_trace=enable_trace,
    )


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value
