"""财务分析工作流的统一业务入口。

本模块刻意独立于 ``app.main``：``app.main`` 后续可以专注作为
FastAPI/ASGI 启动入口，而脚本、接口路由、测试和其他调用方统一依赖
这里的应用层运行器。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from app.workflows.state import WorkflowState, normalize_for_json


GraphFactory = Callable[..., Any]


@dataclass(slots=True)
class FinancialAnalysisResult:
    """应用层运行器返回的稳定结果对象。"""

    status: str | None
    current_stage: str | None
    next_step: str | None
    needs_user_input: bool
    has_error: bool
    assistant_message: str | None
    error_message: str | None
    final_report: str | None
    analysis_result: dict[str, Any]
    report_result: dict[str, Any]
    execution_history: list[dict[str, Any]]
    state: WorkflowState = field(repr=False)

    @classmethod
    def from_state(cls, state: WorkflowState) -> "FinancialAnalysisResult":
        """从原始工作流状态中提取适合接口或命令行返回的结果。"""
        report_result = _dict_or_empty(state.get("report_result"))

        # 最终报告优先使用工作流显式产物；如果没有，则回退到 report_result
        # 中的 Markdown 报告，再回退到历史兼容字段 final_response。
        final_report = (
            state.get("final_report")
            or report_result.get("markdown_report")
            or state.get("final_response")
        )

        return cls(
            status=_optional_str(state.get("status")),
            current_stage=_optional_str(state.get("current_stage")),
            next_step=_optional_str(state.get("next_step")),
            needs_user_input=bool(state.get("needs_user_input")),
            has_error=bool(state.get("has_error")),
            assistant_message=_optional_str(state.get("assistant_message")),
            error_message=_optional_str(state.get("error_message")),
            final_report=_optional_str(final_report),
            analysis_result=_dict_or_empty(state.get("analysis_result")),
            report_result=report_result,
            execution_history=list(state.get("execution_history") or []),
            state=state,
        )

    def to_dict(self, *, include_state: bool = False) -> dict[str, Any]:
        """返回 JSON 安全的字典，便于 FastAPI 响应或命令行打印。"""
        payload: dict[str, Any] = {
            "status": self.status,
            "current_stage": self.current_stage,
            "next_step": self.next_step,
            "needs_user_input": self.needs_user_input,
            "has_error": self.has_error,
            "assistant_message": self.assistant_message,
            "error_message": self.error_message,
            "final_report": self.final_report,
            "analysis_result": self.analysis_result,
            "report_result": self.report_result,
            "execution_history": self.execution_history,
        }

        # 默认不返回完整 state，避免 API 响应过大；调试或恢复流程时可显式打开。
        if include_state:
            payload["state"] = self.state

        return normalize_for_json(payload)


class FinancialAnalysisRunner:
    """负责执行财务分析工作流的应用层服务。

    运行器位于 LangGraph 之上，是业务侧统一入口。它把工作流构建细节收敛到
    一个接口后面，调用方不需要关心 Agent、Skill、Repository 和图节点如何装配。
    """

    def __init__(
        self,
        *,
        workflow_graph: Any | None = None,
        graph_factory: GraphFactory | None = None,
        llm_client: Any | None = None,
        nodes: Any | None = None,
        data_nodes: Any | None = None,
        max_iterations: int = 20,
        enable_trace: bool = False,
        checkpointer: Any | None = None,
        auto_create_tables: bool = True,
        enable_postgres_checkpoint: bool = True,
        checkpoint_conn_string: str | None = None,
    ) -> None:
        self._workflow_graph = workflow_graph
        self._graph_factory = graph_factory
        self._auto_create_tables = auto_create_tables
        self._enable_postgres_checkpoint = enable_postgres_checkpoint
        self._checkpoint_conn_string = checkpoint_conn_string
        self._default_checkpointer_context: Any | None = None
        self._graph_options = {
            "llm_client": llm_client,
            "nodes": nodes,
            "data_nodes": data_nodes,
            "max_iterations": max_iterations,
            "enable_trace": enable_trace,
            "checkpointer": checkpointer,
        }

    @property
    def workflow_graph(self) -> Any:
        """懒加载并复用当前运行器的工作流图。"""
        if self._workflow_graph is None:
            # 工作流图依赖数据库、LLM、TuShare 等外部配置，延迟到真正执行时再构建，
            # 避免导入本业务入口时就触发外部依赖初始化。
            self._ensure_default_checkpointer()
            graph_factory = self._graph_factory or _default_graph_factory
            self._workflow_graph = graph_factory(**self._graph_options)
        return self._workflow_graph

    def run(
        self,
        user_query: str,
        *,
        thread_id: str | None = None,
    ) -> FinancialAnalysisResult:
        """基于用户问题启动一条新的财务分析工作流。"""
        self._ensure_database_schema()
        effective_thread_id = thread_id or f"financial-analysis-{uuid4().hex}"
        state = self.workflow_graph.run(
            user_query=self._normalize_user_query(user_query),
            thread_id=effective_thread_id,
        )
        return FinancialAnalysisResult.from_state(state)

    def continue_from_state(
        self,
        state: WorkflowState,
        *,
        thread_id: str | None = None,
    ) -> FinancialAnalysisResult:
        """从已有工作流状态继续执行。"""
        next_state = self.workflow_graph.continue_from_state(
            state=state,
            thread_id=thread_id,
        )
        return FinancialAnalysisResult.from_state(next_state)

    def resume_with_user_input(
        self,
        state: WorkflowState,
        user_input: str,
    ) -> FinancialAnalysisResult:
        """用户补充缺失信息后，恢复之前暂停的工作流。"""
        next_state = self.workflow_graph.resume_with_user_input(
            state=state,
            user_input=user_input,
        )
        return FinancialAnalysisResult.from_state(next_state)

    def step_once(self, state: WorkflowState) -> FinancialAnalysisResult:
        """只执行一个工作流节点，用于调试或受控执行。"""
        next_state = self.workflow_graph.step_once(state)
        return FinancialAnalysisResult.from_state(next_state)

    def get_checkpoint_state(self, thread_id: str) -> Any:
        """从底层图读取指定线程的 checkpoint 状态。"""
        return self.workflow_graph.get_checkpoint_state(thread_id)

    def get_checkpoint_history(self, thread_id: str) -> list[Any]:
        """从底层图读取指定线程的 checkpoint 历史。"""
        return self.workflow_graph.get_checkpoint_history(thread_id)

    @staticmethod
    def state_to_dict(state: WorkflowState) -> dict[str, Any]:
        """将原始工作流状态转换为适合传输或日志记录的 JSON 安全字典。"""
        return normalize_for_json(state)

    def _ensure_database_schema(self) -> None:
        if not self._auto_create_tables:
            return

        from app.core.database import engine
        from app.models.db_models import Base

        Base.metadata.create_all(bind=engine, checkfirst=True)

    def _ensure_default_checkpointer(self) -> None:
        if (
            self._workflow_graph is not None
            or self._graph_options.get("checkpointer") is not None
            or not self._enable_postgres_checkpoint
        ):
            return

        from app.core.config import settings

        conn_string = self._normalize_postgres_conn_string(
            self._checkpoint_conn_string or settings.database_url
        )
        if not conn_string:
            raise ValueError(
                "Postgres checkpoint is enabled, but no checkpoint_conn_string or DATABASE_URL is configured."
            )

        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:
            raise ImportError(
                "Postgres checkpoint is enabled by default. Install dependencies with "
                "`pip install -r requirements.txt`, or pass enable_postgres_checkpoint=False."
            ) from exc

        context = PostgresSaver.from_conn_string(conn_string)
        checkpointer = context.__enter__()
        try:
            checkpointer.setup()
        except Exception:
            context.__exit__(None, None, None)
            raise

        self._default_checkpointer_context = context
        self._graph_options["checkpointer"] = checkpointer

    def close(self) -> None:
        if self._default_checkpointer_context is None:
            return

        self._default_checkpointer_context.__exit__(None, None, None)
        self._default_checkpointer_context = None

    @staticmethod
    def _normalize_postgres_conn_string(conn_string: str | None) -> str | None:
        if not conn_string:
            return conn_string

        driver_prefixes = (
            "postgresql+psycopg2://",
            "postgresql+psycopg://",
        )
        for prefix in driver_prefixes:
            if conn_string.startswith(prefix):
                return "postgresql://" + conn_string[len(prefix):]

        return conn_string

    @staticmethod
    def _normalize_user_query(user_query: str) -> str:
        if user_query is None:
            return ""
        if not isinstance(user_query, str):
            raise TypeError("user_query 必须是字符串。")
        return user_query.strip()


def run_financial_analysis(
    user_query: str,
    *,
    thread_id: str | None = None,
    **runner_options: Any,
) -> FinancialAnalysisResult:
    """面向简单脚本的一次性便捷函数。"""
    runner = FinancialAnalysisRunner(**runner_options)
    return runner.run(user_query, thread_id=thread_id)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _default_graph_factory(**kwargs: Any) -> Any:
    """默认工作流图工厂，使用函数内导入避免模块导入时初始化外部依赖。"""
    from app.workflows.graph import build_workflow_graph

    return build_workflow_graph(**kwargs)


__all__ = [
    "FinancialAnalysisResult",
    "FinancialAnalysisRunner",
    "run_financial_analysis",
]
