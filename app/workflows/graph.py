"""基于 LangGraph 的工作流编排，支持数据节点并行扇出。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.core.database import SessionLocal
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.data import backfill_plan_skill
from app.skills.data.backfill_plan_skill import BackfillPlanSkill
from app.skills.data.company_profile_fetch_skill import CompanyProfileFetchSkill
from app.skills.data.completeness_check_skill import CompletenessCheckSkill
from app.skills.data.data_preparation_skill import DataPreparationSkill
from app.workflows.nodes import WorkflowNodes
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
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
    """直接以 LangGraph 状态驱动的工作流门面。"""

    def __init__(
        self,
        nodes: WorkflowNodes,
        max_iterations: int = 20,
        enable_trace: bool = False,
    ):
        self.nodes = nodes
        self.max_iterations = max_iterations
        self.enable_trace = enable_trace
        # 单步执行时使用的步骤到节点函数映射。
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
        # 编译后的 LangGraph 供完整运行路径复用。
        self._compiled_graph = self._build_langgraph()

    def run(self, user_query: str) -> WorkflowState:
        """从用户查询启动新的工作流。"""
        return self.continue_from_state(create_initial_state(user_query=user_query))

    def continue_from_state(self, state: WorkflowState) -> WorkflowState:
        """从已有的 LangGraph 原生状态字典继续执行。"""
        if not isinstance(state, dict):
            raise TypeError("continue_from_state requires a WorkflowState dict.")

        # 兼容恢复旧状态或外部传入状态时缺少 next_step 的情况。
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
            # 将运行异常收敛到统一错误节点，保持返回状态结构稳定。
            return self._merge_state_update(failed_state, self.nodes.error_node(failed_state))

    def resume_with_user_input(self, state: WorkflowState, user_input: str) -> WorkflowState:
        """用户补充缺失信息后恢复暂停的工作流。"""
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
        """执行单个节点，并把该节点的局部更新合并回状态。"""
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
        """构建并编译 LangGraph 节点拓扑。"""
        StateGraph, START, END = self._import_langgraph()

        builder = StateGraph(WorkflowState)

        # 注册各阶段节点，节点只返回局部状态更新。
        builder.add_node("supervisor", self._wrap_node(self.nodes.supervisor_node))
        builder.add_node("await_user_input", self._wrap_node(self.nodes.await_user_input_node))
        builder.add_node("data_planner", self._wrap_node(self.nodes.data_planner_node))
        builder.add_node("prepare_company_context", self._wrap_node(self.nodes.prepare_company_context_node))
        builder.add_node("fetch_income_statement", self._wrap_node(self.nodes.fetch_income_statement_node))
        builder.add_node("fetch_balance_sheet", self._wrap_node(self.nodes.fetch_balance_sheet_node))
        builder.add_node("fetch_cashflow_statement", self._wrap_node(self.nodes.fetch_cashflow_statement_node))
        builder.add_node("fetch_financial_indicator", self._wrap_node(self.nodes.fetch_financial_indicator_node))
        builder.add_node("data_merge", self._wrap_node(self.nodes.data_merge_node))
        builder.add_node("completeness_check", self._wrap_node(self.nodes.completeness_check_node))
        builder.add_node("analysis", self._wrap_node(self.nodes.analysis_node))
        builder.add_node("report", self._wrap_node(self.nodes.report_node))
        builder.add_node("reflection", self._wrap_node(self.nodes.reflection_node))
        builder.add_node("finished", self._wrap_node(self.nodes.finish_node))
        builder.add_node("error", self._wrap_node(self.nodes.error_node))

        builder.add_edge(START, "supervisor")
        # 根据状态中的 next_step、status 和错误标记决定下一跳。
        builder.add_conditional_edges("supervisor", self._route_after_node, self._route_path_map(END))
        builder.add_edge("data_planner", "prepare_company_context")
        builder.add_conditional_edges("prepare_company_context", self._route_data_parts, self._data_route_path_map())

        # 多个数据抓取节点可以并行执行，最后统一汇聚到 data_merge。
        for fetch_node in (
            "fetch_income_statement",
            "fetch_balance_sheet",
            "fetch_cashflow_statement",
            "fetch_financial_indicator",
        ):
            builder.add_edge(fetch_node, "data_merge")

        # builder.add_conditional_edges("data_merge", self._route_after_node, self._route_path_map(END))
        builder.add_edge("data_merge", "completeness_check")
        for node_name in ("analysis", "report", "reflection"):
            builder.add_conditional_edges(node_name, self._route_after_node, self._route_path_map(END))

        builder.add_edge("await_user_input", END)
        builder.add_edge("finished", END)
        builder.add_edge("error", END)

        return builder.compile()

    @staticmethod
    def _import_langgraph():
        """延迟导入 LangGraph，并在依赖缺失时给出明确错误。"""
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
        """定义普通工作流阶段的路由名到节点名映射。"""
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
        """定义数据分片路由名到抓取节点名的映射。"""
        return {
            DATA_PART_INCOME: "fetch_income_statement",
            DATA_PART_BALANCE: "fetch_balance_sheet",
            DATA_PART_CASHFLOW: "fetch_cashflow_statement",
            DATA_PART_INDICATORS: "fetch_financial_indicator",
            "data_merge": "data_merge",
            "error": "error",
        }

    def _wrap_node(self, node_fn: Callable[[WorkflowState], dict]) -> Callable[[WorkflowState], dict]:
        """包装节点函数，在开启追踪时输出执行前后的状态摘要。"""
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
        """根据节点执行后的状态选择下一条 LangGraph 边。"""
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
        """把数据规划结果转换成需要并行触发的数据抓取路由。"""
        if state.get("has_error") or state.get("status") == WorkflowStatus.ERROR:
            return ["error"]

        if state.get("need_backfill"):
            if int(state.get("already_backfill")) <= 2:
                routes = [
                    part
                    for part in state.get("need_backfill").keys()
                    if part in {
                        DATA_PART_INCOME,
                        DATA_PART_BALANCE,
                        DATA_PART_CASHFLOW,
                        DATA_PART_INDICATORS,
                    }
                ]
            else:
                return ["data_finalize"]
        else:
            routes = [
                part
                for part in state.get("required_data_parts", [])
                if part in {
                    DATA_PART_INCOME,
                    DATA_PART_BALANCE,
                    DATA_PART_CASHFLOW,
                    DATA_PART_INDICATORS,
                }
            ]
        return routes or ["data_merge"]

    @staticmethod
    def _infer_entry_step(state: WorkflowState) -> WorkflowStep:
        """根据已有状态推断恢复执行时的入口步骤。"""
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
        """合并节点局部更新，列表型观测字段采用追加语义。"""
        merged = dict(state)
        for key, value in update.items():
            if key in {"execution_history", "data_part_results", "data_fetch_errors"}:
                merged[key] = list(merged.get(key, [])) + list(value or [])
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _trace(state: WorkflowState, prefix: str) -> None:
        """输出便于调试的工作流状态摘要。"""
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
        """将 WorkflowState 转换为便于 JSON 序列化的字典。"""
        return normalize_for_json(dict(state))


def build_workflow_graph(
    *,
    llm_client: Optional[Any] = None,
    nodes: Optional[WorkflowNodes] = None,
    max_iterations: int = 20,
    enable_trace: bool = False,
) -> WorkflowGraph:
    """构建默认的 LangGraph 原生工作流图。"""
    if nodes is None:
        # 延迟创建默认 Agent，方便测试或外部调用时注入自定义节点。
        from app.agents.analysis_agent import AnalysisAgent
        from app.agents.data_agent import DataAgent
        from app.agents.reflection_agent import ReflectionAgent
        from app.agents.report_agent import ReportAgent
        from app.agents.supervisor_agent import SupervisorAgent
        from app.llms.openai_client import OpenAIClient
        from app.skills.planning.planning_skill import PlanningSkill
        from app.repositories.company_repo import CompanyRepository
        from app.services.tushare_service import TushareServiceConfig
        from app.core.config import settings

        llm_client = llm_client or OpenAIClient()
        planning_skill = PlanningSkill(llm_client=llm_client)

        company_repo = CompanyRepository()
        income_repo = IncomeRepository()
        indicator_repo = FinaIndicatorRepository()
        cashflow_repo = CashFlowRepository()
        balance_repo = BalanceSheetRepository()

        config = TushareServiceConfig(settings.TuShare_Token)
        tushare_client = TushareService(config)
        company_resolver = CompanyResolver(company_repo, tushare_client)
        session_factory = SessionLocal
        time_range_parser = TimeRangeParser()
        completeness_checker_capability = DataCompletenessChecker()
        completeness_checker_skill = CompletenessCheckSkill(completeness_checker_capability)

        nodes = WorkflowNodes(
            supervisor_agent=SupervisorAgent(planning_skill=planning_skill),
            data_agent=DataAgent(),
            analysis_agent=AnalysisAgent(),
            report_agent=ReportAgent(),
            reflection_agent=ReflectionAgent(),
            company_profile_fetch_skill=CompanyProfileFetchSkill(company_resolver, session_factory),
            data_preparation_skill=DataPreparationSkill(
                time_range_parser=time_range_parser,
                income_repo=income_repo,
                indicator_repo=indicator_repo,
                cashflow_repo=cashflow_repo,
                balance_repo=balance_repo,
                tushare_service=tushare_client,
                session_factory=session_factory
            ),
            completeness_checker_skill=completeness_checker_skill,
            backfill_plan_skill=BackfillPlanSkill(llm_client),
        )

    return WorkflowGraph(
        nodes=nodes,
        max_iterations=max_iterations,
        enable_trace=enable_trace,
    )


def _enum_value(value: Any) -> Any:
    """返回枚举的原始值；非枚举对象保持不变。"""
    return value.value if hasattr(value, "value") else value
