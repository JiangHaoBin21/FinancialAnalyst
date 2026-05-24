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
from app.skills.data.backfill_plan_skill import BackfillPlanSkill
from app.skills.data.company_profile_fetch_skill import CompanyProfileFetchSkill
from app.skills.data.completeness_check_skill import CompletenessCheckSkill
from app.skills.data.data_preparation_skill import DataPreparationSkill
from app.skills.data.required_parts_skill import RequiredPartsSkill
from app.skills.supervisor.review_skill import SupervisorReviewSkill
from app.workflows.nodes import WorkflowNodes
from app.workflows.state import (
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    create_initial_state,
    error_update,
    make_json_safe,
    normalize_for_json,
    next_workflow_step,
)
from app.workflows.subgraphs.data_graph import build_data_subgraph
from app.workflows.subgraphs.data_nodes import DataSubgraphNodes


class WorkflowGraph:
    """直接以 LangGraph 状态驱动的工作流门面。"""

    def __init__(
        self,
        nodes: WorkflowNodes,
        data_nodes: DataSubgraphNodes,
        max_iterations: int = 20,
        enable_trace: bool = False,
        checkpointer: Any | None = None,
    ):
        self.nodes = nodes
        self.data_nodes = data_nodes
        self.max_iterations = max_iterations
        self.enable_trace = enable_trace
        self.checkpointer = checkpointer
        # 单步执行时使用的步骤到节点函数映射。
        self._route_table: dict[str, Callable[[WorkflowState], dict]] = {
            WorkflowStep.SUPERVISOR.value: self.nodes.supervisor_node,
            WorkflowStep.AWAIT_USER_INPUT.value: self.nodes.await_user_input_node,
            WorkflowStep.DATA.value: self._run_data_stage_once,
            WorkflowStep.ANALYSIS.value: self.nodes.analysis_node,
            WorkflowStep.REPORT.value: self.nodes.report_node,
            WorkflowStep.REFLECTION.value: self.nodes.reflection_node,
            WorkflowStep.FINISHED.value: self.nodes.finish_node,
            WorkflowStep.ERROR.value: self.nodes.error_node,
        }
        # 编译后的 LangGraph 供完整运行路径复用。
        self._compiled_graph = self._build_langgraph()

    def run(self, user_query: str, thread_id: str | None = None) -> WorkflowState:
        """从用户查询启动新的工作流。"""
        return self.continue_from_state(create_initial_state(user_query=user_query), thread_id=thread_id)

    def continue_from_state(self, state: WorkflowState, thread_id: str | None = None) -> WorkflowState:
        """从已有的 LangGraph 原生状态字典继续执行。"""
        if not isinstance(state, dict):
            raise TypeError("continue_from_state requires a WorkflowState dict.")

        # 兼容恢复旧状态或外部传入状态时缺少 next_step 的情况。
        if state.get("next_step") is None:
            state = {**state, "next_step": self._infer_entry_step(state)}
        config = {
            "recursion_limit": self._recursion_limit,
        }

        if thread_id:
            config["configurable"] = {
                "thread_id": thread_id,
            }
        try:
            return self._compiled_graph.invoke(
                state,
                config=config,
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
                "status": WorkflowStatus.NEEDS_USER_INPUT.value,
                "next_step": WorkflowStep.AWAIT_USER_INPUT.value,
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
            "current_stage": WorkflowStep.SUPERVISOR.value,
            "next_step": WorkflowStep.SUPERVISOR.value,
            "status": WorkflowStatus.INIT.value,
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

    def _run_data_stage_once(self, state: WorkflowState) -> dict:
        data_subgraph = build_data_subgraph(
            nodes=self.data_nodes,
            wrap_node=self._wrap_node,
        )

        result_state = data_subgraph.invoke(
            state,
            config={"recursion_limit": self._recursion_limit},
        )

        update = {}

        append_keys = {"execution_history", "data_part_results", "data_fetch_errors"}

        for key, value in result_state.items():
            old_value = state.get(key)

            if key in append_keys:
                old_list = list(old_value or [])
                new_list = list(value or [])
                update[key] = new_list[len(old_list):]
            elif old_value != value:
                update[key] = value

        return update

    @property
    def _recursion_limit(self) -> int:
        return max(self.max_iterations + 8, 16)

    def _build_langgraph(self):
        """构建并编译主工作流图。

        主图只负责编排大阶段：
        supervisor -> data_stage -> analysis -> report -> reflection -> finished/error
        Data 阶段内部细节由 DataSubgraph 管理。
        """
        StateGraph, START, END = self._import_langgraph()

        builder = StateGraph(WorkflowState)

        data_subgraph = build_data_subgraph(
            nodes=self.data_nodes,
            wrap_node=self._wrap_node,
        )

        builder.add_node("supervisor", self._wrap_node(self.nodes.supervisor_node))
        builder.add_node("await_user_input", self._wrap_node(self.nodes.await_user_input_node))
        builder.add_node("data_stage", data_subgraph)
        builder.add_node("analysis", self._wrap_node(self.nodes.analysis_node))
        builder.add_node("report", self._wrap_node(self.nodes.report_node))
        builder.add_node("reflection", self._wrap_node(self.nodes.reflection_node))
        builder.add_node("finished", self._wrap_node(self.nodes.finish_node))
        builder.add_node("error", self._wrap_node(self.nodes.error_node))

        builder.add_edge(START, "supervisor")

        builder.add_conditional_edges(
            "supervisor",
            self._route_after_node,
            self._route_path_map(END),
        )

        builder.add_edge("data_stage", "supervisor")
        builder.add_edge("analysis", "supervisor")
        builder.add_edge("report", "supervisor")
        builder.add_edge("reflection", "supervisor")

        builder.add_edge("await_user_input", END)
        builder.add_edge("finished", END)
        builder.add_edge("error", END)

        return builder.compile(checkpointer=self.checkpointer)

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
            "data": "data_stage",
            "analysis": "analysis",
            "report": "report",
            "reflection": "reflection",
            "finished": "finished",
            "error": "error",
            "end": end_marker,
        }

    def _wrap_node(self, node_fn: Callable[[WorkflowState], dict]) -> Callable[[WorkflowState], dict]:
        """包装节点函数，在开启追踪时输出执行前后的状态摘要。"""
        def wrapped(state: WorkflowState) -> dict:
            if self.enable_trace:
                self._trace(state, prefix=f"[langgraph.before:{node_fn.__name__}]")

            update = make_json_safe(node_fn(state))

            if self.enable_trace:
                preview_state = self._merge_state_update(state, update)
                self._trace(preview_state, prefix=f"[langgraph.after:{node_fn.__name__}]")

            return update

        return wrapped

    def _route_after_node(self, state: WorkflowState) -> str:
        """根据节点执行后的状态选择下一条 LangGraph 边。"""
        if state.get("current_stage") == WorkflowStep.FINISHED.value or state.get("is_finished"):
            return "end" if state.get("current_stage") == WorkflowStep.FINISHED.value else "finished"

        if state.get("next_step") == WorkflowStep.AWAIT_USER_INPUT.value or state.get("status") == WorkflowStatus.NEEDS_USER_INPUT.value:
            return "end" if state.get("current_stage") == WorkflowStep.AWAIT_USER_INPUT.value else "await_user_input"

        if state.get("next_step") == WorkflowStep.ERROR.value or state.get("has_error") or state.get("status") == WorkflowStatus.ERROR.value:
            return "end" if state.get("current_stage") == WorkflowStep.ERROR.value else "error"

        next_step = state.get("next_step")
        if next_step == WorkflowStep.DATA.value:
            return "data"
        if next_step == WorkflowStep.ANALYSIS.value:
            return "analysis"
        if next_step == WorkflowStep.REPORT.value:
            return "report"
        if next_step == WorkflowStep.REFLECTION.value:
            return "reflection"
        if next_step == WorkflowStep.FINISHED.value:
            return "finished"

        return "error"


    @staticmethod
    def _infer_entry_step(state: WorkflowState) -> str:
        """根据已有状态推断恢复执行时的入口步骤。"""
        if state.get("has_error") or state.get("status") == WorkflowStatus.ERROR.value:
            return WorkflowStep.ERROR.value
        if state.get("is_finished") or state.get("status") == WorkflowStatus.FINISHED.value:
            return WorkflowStep.FINISHED.value
        if state.get("needs_user_input") or state.get("status") == WorkflowStatus.NEEDS_USER_INPUT.value:
            return WorkflowStep.AWAIT_USER_INPUT.value
        if state.get("task_plan"):
            return next_workflow_step(
                state.get("task_plan", []),
                state.get("current_step_index", 0),
            )
        return WorkflowStep.SUPERVISOR.value

    @staticmethod
    def _merge_state_update(state: WorkflowState, update: dict) -> WorkflowState:
        """合并节点局部更新，列表型观测字段采用追加语义。"""
        merged = dict(state)
        for key, value in update.items():
            value = make_json_safe(value)
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

    def get_checkpoint_state(self, thread_id: str):
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        return self._compiled_graph.get_state(config)

    def get_checkpoint_history(self, thread_id: str):
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        return list(self._compiled_graph.get_state_history(config))


def build_workflow_graph(
    *,
    llm_client: Optional[Any] = None,
    nodes: Optional[WorkflowNodes] = None,
    data_nodes: Optional[DataSubgraphNodes] = None,
    max_iterations: int = 20,
    enable_trace: bool = False,
    checkpointer: Any | None = None,
) -> WorkflowGraph:
    """构建默认的 LangGraph 原生工作流图。"""

    # 延迟创建默认 Agent / Skill，方便测试或外部调用时注入自定义节点。
    if nodes is None or data_nodes is None:
        from app.agents.analysis_agent import AnalysisAgent
        from app.agents.data_agent import DataAgent
        from app.agents.reflection_agent import ReflectionAgent
        from app.agents.report_agent import ReportAgent
        from app.agents.supervisor_agent import SupervisorAgent
        from app.core.config import settings
        from app.llms.openai_client import OpenAIClient
        from app.repositories.company_repo import CompanyRepository
        from app.services.tushare_service import TushareServiceConfig
        from app.skills.supervisor.planning_skill import PlanningSkill

        llm_client = llm_client or OpenAIClient()

        # =========================
        # 1. 构造主图依赖
        # =========================
        if nodes is None:
            planning_skill = PlanningSkill(llm_client=llm_client)
            review_skill = SupervisorReviewSkill(llm_client=llm_client)

            nodes = WorkflowNodes(
                supervisor_agent=SupervisorAgent(planning_skill=planning_skill, review_skill=review_skill),
                analysis_agent=AnalysisAgent(llm_client=llm_client),
                report_agent=ReportAgent(llm_client=llm_client),
                reflection_agent=ReflectionAgent(),
            )

        # =========================
        # 2. 构造 DataSubgraph 依赖
        # =========================
        if data_nodes is None:
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
            completeness_checker_skill = CompletenessCheckSkill(
                completeness_checker_capability
            )

            backfill_plan_skill = BackfillPlanSkill(llm_client)
            required_parts_skill = RequiredPartsSkill(llm_client)

            data_agent = DataAgent(
                required_parts_skill=required_parts_skill,
                backfill_plan_skill=backfill_plan_skill,
            )

            data_preparation_skill = DataPreparationSkill(
                time_range_parser=time_range_parser,
                income_repo=income_repo,
                indicator_repo=indicator_repo,
                cashflow_repo=cashflow_repo,
                balance_repo=balance_repo,
                tushare_service=tushare_client,
                session_factory=session_factory,
            )

            data_nodes = DataSubgraphNodes(
                data_agent=data_agent,
                company_profile_fetch_skill=CompanyProfileFetchSkill(
                    company_resolver,
                    session_factory,
                ),
                data_preparation_skill=data_preparation_skill,
                completeness_checker_skill=completeness_checker_skill,
            )

    return WorkflowGraph(
        nodes=nodes,
        data_nodes=data_nodes,
        max_iterations=max_iterations,
        enable_trace=enable_trace,
        checkpointer=checkpointer,
    )


def _enum_value(value: Any) -> Any:
    """返回枚举的原始值；非枚举对象保持不变。"""
    return value.value if hasattr(value, "value") else value
