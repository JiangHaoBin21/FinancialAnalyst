from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from threading import Lock
from typing import Any

from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from app.agents.analysis_agent import AnalysisAgent
from app.agents.data_agent import DataAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.report_agent import ReportAgent
from app.agents.supervisor_agent import SupervisorAgent
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.llms.openai_client import OpenAIClient
from app.models.db_models import Base
from app.repositories.balance_repo import BalanceSheetRepository
from app.repositories.cashflow_repo import CashFlowRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.income_repo import IncomeRepository
from app.repositories.indicator_repo import FinaIndicatorRepository
from app.services.tushare_service import TushareService, TushareServiceConfig
from app.skills.capabilities.company_resolver import CompanyResolver
from app.skills.capabilities.data_completeness_checker import DataCompletenessChecker
from app.skills.capabilities.time_range_parser import TimeRangeParser
from app.skills.data.backfill_plan_skill import BackfillPlanSkill
from app.skills.data.company_profile_fetch_skill import CompanyProfileFetchSkill
from app.skills.data.completeness_check_skill import CompletenessCheckSkill
from app.skills.data.data_preparation_skill import DataPreparationSkill
from app.skills.data.required_parts_skill import RequiredPartsSkill
from app.skills.supervisor.planning_skill import PlanningSkill
from app.skills.supervisor.review_skill import SupervisorReviewSkill
from app.workflows.graph import WorkflowGraph
from app.workflows.nodes import WorkflowNodes
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    WorkflowState,
    WorkflowStep,
    normalize_for_json,
)
from app.workflows.subgraphs.data_nodes import DataSubgraphNodes
from test_supervisor_data_nodes import (
    EXPECTED_GRAPH_NODES as DATA_EXPECTED_GRAPH_NODES,
    assert_graph_node_outputs,
    assert_state_json_safe,
    enum_value,
    print_execution_history,
    print_node_run_results,
    print_step,
    require,
)


DEFAULT_QUERY = (
    "请分析 300750.SZ 在 2023 年财务表现，覆盖盈利能力、偿债能力、"
    "现金流质量和关键财务指标，生成正式财务分析报告，并进行最终质量审查。"
)

MAX_STAGE_OUTPUT_PREVIEW_LENGTH = 3000

FINANCIAL_PARTS = [
    DATA_PART_INCOME,
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INDICATORS,
]

REQUIRED_MODEL_TABLES = [
    "dim_company",
    "fact_income",
    "fact_balance_sheet",
    "fact_cashflow",
    "fact_fina_indicator",
]

EXPECTED_GRAPH_NODES = set(DATA_EXPECTED_GRAPH_NODES) | {
    "analysis_node",
    "report_node",
    "reflection_node",
}

EXECUTION_AGENT_TO_NODE = {
    "SupervisorAgent": "supervisor_node",
    "DataAgent": "data_planner_node",
    "DataNode:company context": "prepare_company_context_node",
    f"DataNode:{DATA_PART_INCOME}": "fetch_income_statement_node",
    f"DataNode:{DATA_PART_BALANCE}": "fetch_balance_sheet_node",
    f"DataNode:{DATA_PART_CASHFLOW}": "fetch_cashflow_statement_node",
    f"DataNode:{DATA_PART_INDICATORS}": "fetch_financial_indicator_node",
    "DataNode:merge node": "data_merge_node",
    "DataNode:completeness check": "completeness_check_node",
    "DataNode:backfill plan": "backfill_planner_node",
    "DataNode:finalize": "data_finalize_node",
    "AnalysisAgent": "analysis_node",
    "ReportAgent": "report_node",
    "ReflectionAgent": "reflection_node",
}

VALID_ANALYSIS_STATUSES = {
    "analysis_done",
    "analysis_partial",
    "needs_more_data",
    "analysis_failed",
}
NON_FAILED_ANALYSIS_STATUSES = VALID_ANALYSIS_STATUSES - {"analysis_failed"}
VALID_REPORT_STATUSES = {
    "report_ready",
    "report_partial",
    "report_failed",
}
NON_FAILED_REPORT_STATUSES = VALID_REPORT_STATUSES - {"report_failed"}
VALID_REPORT_TYPES = {
    "financial_analysis",
    "investment_reference",
    "risk_analysis",
    "general_report",
}
VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}
VALID_REFLECTION_STATUSES = {
    "reflection_done",
    "reflection_failed",
}
NON_FAILED_REFLECTION_STATUSES = VALID_REFLECTION_STATUSES - {"reflection_failed"}
VALID_REFLECTION_DECISIONS = {
    "pass",
    "pass_with_minor_revision",
    "needs_report_regeneration",
    "needs_analysis_revision",
    "needs_more_data",
    "failed",
}
REFLECTION_DECISION_TO_NEXT_STAGE = {
    "pass": "finished",
    "pass_with_minor_revision": "finished",
    "needs_report_regeneration": "report",
    "needs_analysis_revision": "analysis",
    "needs_more_data": "data",
    "failed": "error",
}
DELIVERABLE_REFLECTION_DECISIONS = {"pass", "pass_with_minor_revision"}
VALID_REFLECTION_ISSUE_SEVERITIES = {"low", "medium", "high", "critical"}


class ReActToolCallLoggingLLMClient:
    """测试脚本用的 LLM 代理：只打印 Analysis ReAct 阶段的 tool_calls。"""

    def __init__(self, wrapped_client: OpenAIClient):
        self.wrapped_client = wrapped_client
        self._react_round = 0

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list | None = None,
        **kwargs: Any,
    ) -> Any:
        result = self.wrapped_client.generate(
            messages=messages,
            tools=tools,
            **kwargs,
        )

        if tools:
            if not any(
                message.get("role") in {"assistant", "tool"}
                for message in messages
            ):
                self._react_round = 0
            self._react_round += 1
            print_analysis_react_tool_calls(
                round_number=self._react_round,
                assistant_message=result,
            )

        return result

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        return self.wrapped_client.chat(messages=messages, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wrapped_client, name)


class ChineseArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法:")

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法:")
            .replace("options:", "选项:")
        )


def parse_args() -> argparse.Namespace:
    parser = ChineseArgumentParser(
        add_help=False,
        description=(
            "运行 supervisor + data + analysis + report + reflection 阶段的真实集成测试，"
            "覆盖图调度、真实 Agent、真实 LLM、真实数据库和必要时的 TuShare 回源。"
        )
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示帮助信息并退出。",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        metavar="文本",
        help="发送给真实 SupervisorAgent 和规划 LLM 的用户输入；默认会要求生成报告并执行最终质量审查。",
    )
    parser.add_argument(
        "--full-results",
        action="store_true",
        help="打印完整节点返回结果；默认只打印压缩预览。",
    )
    return parser.parse_args()


def build_real_nodes() -> tuple[WorkflowNodes, DataSubgraphNodes]:
    settings.validate()

    llm_client = OpenAIClient()
    planning_skill = PlanningSkill(llm_client=llm_client)
    review_skill = SupervisorReviewSkill(llm_client=llm_client)
    required_parts_skill = RequiredPartsSkill(llm_client=llm_client)
    backfill_plan_skill = BackfillPlanSkill(llm_client=llm_client)
    tushare_service = TushareService(TushareServiceConfig(token=settings.TuShare_Token))

    company_repo = CompanyRepository()
    income_repo = IncomeRepository()
    balance_repo = BalanceSheetRepository()
    cashflow_repo = CashFlowRepository()
    indicator_repo = FinaIndicatorRepository()

    company_resolver = CompanyResolver(
        company_repo=company_repo,
        tushare_service=tushare_service,
    )

    nodes = WorkflowNodes(
        supervisor_agent=SupervisorAgent(
            planning_skill=planning_skill,
            review_skill=review_skill,
        ),
        analysis_agent=AnalysisAgent(
            llm_client=ReActToolCallLoggingLLMClient(llm_client),
        ),
        report_agent=ReportAgent(llm_client=llm_client),
        reflection_agent=ReflectionAgent(llm_client=llm_client),
    )

    data_nodes = DataSubgraphNodes(
        data_agent=DataAgent(
            required_parts_skill=required_parts_skill,
            backfill_plan_skill=backfill_plan_skill,
        ),
        company_profile_fetch_skill=CompanyProfileFetchSkill(
            company_resolver=company_resolver,
            session_factory=SessionLocal,
        ),
        data_preparation_skill=DataPreparationSkill(
            time_range_parser=TimeRangeParser(),
            income_repo=income_repo,
            indicator_repo=indicator_repo,
            cashflow_repo=cashflow_repo,
            balance_repo=balance_repo,
            tushare_service=tushare_service,
            session_factory=SessionLocal,
        ),
        completeness_checker_skill=CompletenessCheckSkill(DataCompletenessChecker()),
    )

    return nodes, data_nodes


def assert_real_dependencies(
    nodes: WorkflowNodes,
    data_nodes: DataSubgraphNodes,
) -> None:
    print_step("真实依赖检查")

    supervisor = nodes.supervisor_agent
    data_agent = data_nodes.data_agent
    company_profile_skill = data_nodes.company_profile_fetch_skill
    data_preparation_skill = data_nodes.data_preparation_skill

    require(
        isinstance(supervisor.planning_skill.llm_client, OpenAIClient),
        "Supervisor 规划 skill 未使用 OpenAIClient。",
    )
    require(
        isinstance(supervisor.review_skill.llm_client, OpenAIClient),
        "Supervisor 审查 skill 未使用 OpenAIClient。",
    )
    analysis_llm_client = nodes.analysis_agent.llm_client
    require(
        isinstance(analysis_llm_client, ReActToolCallLoggingLLMClient)
        and isinstance(analysis_llm_client.wrapped_client, OpenAIClient),
        "AnalysisAgent 未通过 OpenAIClient 执行 ReAct tool_calls 观测。",
    )
    require(
        isinstance(nodes.report_agent.llm_client, OpenAIClient),
        "ReportAgent 未使用 OpenAIClient。",
    )
    require(
        isinstance(nodes.reflection_agent.llm_client, OpenAIClient),
        "ReflectionAgent 未使用 OpenAIClient。",
    )
    require(
        isinstance(data_agent.required_parts_skill.llm_client, OpenAIClient),
        "RequiredPartsSkill 未使用 OpenAIClient。",
    )
    require(
        isinstance(data_agent.backfill_plan_skill.llm_client, OpenAIClient),
        "BackfillPlanSkill 未使用 OpenAIClient。",
    )
    require(
        company_profile_skill.session_factory is SessionLocal,
        "CompanyProfileFetchSkill 未使用 SessionLocal。",
    )
    require(
        data_preparation_skill.session_factory is SessionLocal,
        "DataPreparationSkill 未使用 SessionLocal。",
    )
    require(
        isinstance(data_preparation_skill.tushare_service, TushareService),
        "DataPreparationSkill 未使用 TushareService。",
    )
    require(
        isinstance(
            company_profile_skill.company_resolver.tushare_service,
            TushareService,
        ),
        "CompanyResolver 未使用 TushareService。",
    )

    print("未注入 mock/fake/stub 依赖；Analysis LLM 仅包了一层打印代理。")
    print("LLM 客户端: OpenAIClient")
    print("Analysis ReAct 观测: 打印每轮大模型返回的 tool_calls")
    print("Report 生成: OpenAIClient")
    print("Reflection 审查: OpenAIClient")
    print("数据库会话工厂: SessionLocal")
    print("行情/财务数据服务: TushareService")


def create_missing_tables_from_orm() -> None:
    print_step("ORM 自动建表")
    Base.metadata.create_all(bind=engine)
    print(
        "Base.metadata.create_all 已完成：不存在的表已根据当前 ORM 模型创建。"
    )
    print(
        "注意：create_all 不会修改已有表结构；下一步会继续检查数据库表结构是否与 ORM 一致。"
    )


def assert_database_schema_matches_models() -> None:
    print_step("数据库结构检查")

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [
        table_name
        for table_name in REQUIRED_MODEL_TABLES
        if table_name not in existing_tables
    ]
    require(
        not missing_tables,
        f"数据库缺少必需表: {missing_tables}",
    )

    schema_issues: dict[str, list[str]] = {}
    for table_name in REQUIRED_MODEL_TABLES:
        model_table = Base.metadata.tables[table_name]
        expected_columns = {column.name for column in model_table.columns}
        actual_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }
        missing_columns = sorted(expected_columns - actual_columns)
        if missing_columns:
            schema_issues[table_name] = missing_columns

    if schema_issues:
        print("数据库表结构与 ORM 模型不一致:")
        for table_name, columns in schema_issues.items():
            print(f"  - {table_name}: 缺少字段 {columns}")
        raise AssertionError("数据库表结构与 ORM 模型不同步。")

    print("数据库表结构已匹配本测试所需的 ORM 字段。")


def attach_node_result_recorder_with_stage_prints(
    nodes: WorkflowNodes,
    data_nodes: DataSubgraphNodes,
    *,
    full_results: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lock = Lock()

    def wrap_node(node_name: str, node_fn):
        def wrapped(state: WorkflowState) -> dict[str, Any]:
            try:
                update = node_fn(state)
            except Exception as exc:
                with lock:
                    records.append(
                        {
                            "node_name": node_name,
                            "success": False,
                            "exception_type": type(exc).__name__,
                            "exception_message": str(exc),
                        }
                    )
                raise

            with lock:
                records.append(
                    {
                        "node_name": node_name,
                        "success": not bool(update.get("has_error")),
                        "update": update,
                    }
                )
                print_stage_output_after_node(
                    node_name=node_name,
                    state=state,
                    update=update,
                    full_results=full_results,
                )
            return update

        return wrapped

    for target, node_names in (
        (
            nodes,
            [
                "supervisor_node",
                "await_user_input_node",
                "analysis_node",
                "report_node",
                "reflection_node",
                "finish_node",
                "error_node",
            ],
        ),
        (
            data_nodes,
            [
                "data_planner_node",
                "prepare_company_context_node",
                "fetch_income_statement_node",
                "fetch_balance_sheet_node",
                "fetch_cashflow_statement_node",
                "fetch_financial_indicator_node",
                "data_merge_node",
                "completeness_check_node",
                "backfill_planner_node",
                "data_finalize_node",
                "data_error_node",
            ],
        ),
    ):
        for node_name in node_names:
            original_node = getattr(target, node_name)
            setattr(target, node_name, wrap_node(node_name, original_node))

    return records


def print_stage_output_after_node(
    *,
    node_name: str,
    state: WorkflowState,
    update: dict[str, Any],
    full_results: bool,
) -> None:
    merged_state = {**state, **update}
    if node_name == "supervisor_node":
        print_supervisor_stage_output(merged_state, update, full_results=full_results)
    elif node_name == "data_finalize_node":
        print_data_stage_output(merged_state, full_results=full_results)
    elif node_name == "data_error_node":
        print_data_stage_output(merged_state, full_results=full_results)
    elif node_name == "analysis_node":
        print_analysis_stage_output(merged_state, full_results=full_results)
    elif node_name == "report_node":
        print_report_stage_output(merged_state, full_results=full_results)
    elif node_name == "reflection_node":
        print_reflection_stage_output(merged_state, full_results=full_results)


def print_analysis_react_tool_calls(
    *,
    round_number: int,
    assistant_message: Any,
) -> None:
    tool_calls = getattr(assistant_message, "tool_calls", None) or []
    payload = {
        "轮次": round_number,
        "tool_calls数量": len(tool_calls),
        "tool_calls": [
            serialize_tool_call_for_print(tool_call)
            for tool_call in tool_calls
        ],
    }
    if not tool_calls:
        payload["说明"] = "本轮模型未返回 tool_calls，ReAct 证据收集结束。"

    print_stage_payload(
        "Analysis ReAct 模型返回 tool_calls",
        payload,
        full_results=True,
    )


def serialize_tool_call_for_print(tool_call: Any) -> dict[str, Any]:
    function = getattr(tool_call, "function", None)
    raw_arguments = getattr(function, "arguments", None)
    parsed_arguments = parse_tool_arguments_for_print(raw_arguments)

    return {
        "id": getattr(tool_call, "id", None),
        "type": getattr(tool_call, "type", None),
        "function": {
            "name": getattr(function, "name", None),
            "arguments": parsed_arguments,
            "raw_arguments": raw_arguments,
        },
    }


def parse_tool_arguments_for_print(raw_arguments: Any) -> Any:
    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return raw_arguments

    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError:
        return raw_arguments


def print_supervisor_stage_output(
    state: WorkflowState,
    update: dict[str, Any],
    *,
    full_results: bool,
) -> None:
    stage_kind = "规划" if not update.get("trans_message") else "审查"
    payload = {
        "阶段类型": stage_kind,
        "状态": state.get("status"),
        "任务类型": state.get("task_type"),
        "公司名称": state.get("company_name"),
        "股票代码": state.get("ts_code"),
        "时间范围": state.get("time_range"),
        "分析重点": state.get("analysis_focus"),
        "输出模式": state.get("output_mode"),
        "任务计划": state.get("task_plan"),
        "当前步骤索引": state.get("current_step_index"),
        "下一步": state.get("next_step"),
        "是否需要用户补充": state.get("needs_user_input"),
        "缺失字段": state.get("missing_fields"),
        "规划消息": state.get("planner_message"),
        "阶段传递消息": state.get("trans_message"),
        "助手消息": state.get("assistant_message"),
    }
    if full_results:
        payload["原始规划响应"] = state.get("raw_planner_response")
        payload["阶段产物"] = state.get("stage_outputs")

    print_stage_payload("Supervisor 阶段成果", payload, full_results=full_results)


def print_data_stage_output(
    state: WorkflowState,
    *,
    full_results: bool,
) -> None:
    payload = {
        "状态": state.get("status"),
        "当前阶段": state.get("current_stage"),
        "下一步": state.get("next_step"),
        "所需数据分片": state.get("required_data_parts"),
        "公司画像": state.get("company_profile"),
        "财务数据摘要": summarize_financial_data(
            state.get("financial_data") or {}
        ),
        "财务数据": state.get("financial_data"),
        "数据完整性检查结果": state.get("data_completeness_check_result"),
        "是否需要回填": state.get("need_backfill"),
        "已回填次数": state.get("already_backfill"),
        "数据抓取错误": state.get("data_fetch_errors"),
        "数据摘要": state.get("data_summary"),
        "阶段传递消息": state.get("trans_message"),
        "助手消息": state.get("assistant_message"),
        "错误消息": state.get("error_message"),
    }
    if full_results:
        payload["财务数据"] = state.get("financial_data")
        payload["数据分片结果"] = state.get("data_part_results")

    print_stage_payload("Data 阶段成果", payload, full_results=full_results)


def print_analysis_stage_output(
    state: WorkflowState,
    *,
    full_results: bool,
) -> None:
    analysis_result = state.get("analysis_result") or {}
    payload = {
        "状态": state.get("status"),
        "当前阶段": state.get("current_stage"),
        "下一步": state.get("next_step"),
        "分析状态": analysis_result.get("status"),
        "摘要": analysis_result.get("summary"),
        "分析维度": analysis_result.get("dimensions"),
        "数据限制": analysis_result.get("data_limitations"),
        "结论": analysis_result.get("conclusion"),
        "证据摘要": summarize_evidence(analysis_result.get("evidence")),
        "助手消息": state.get("assistant_message"),
        "错误消息": state.get("error_message"),
    }
    if full_results:
        payload["完整分析结果"] = analysis_result

    print_stage_payload("Analysis 阶段成果", payload, full_results=full_results)


def print_report_stage_output(
    state: WorkflowState,
    *,
    full_results: bool,
) -> None:
    report_result = state.get("report_result") or {}
    markdown_report = report_result.get("markdown_report") or ""
    payload = {
        "状态": state.get("status"),
        "当前阶段": state.get("current_stage"),
        "下一步": state.get("next_step"),
        "报告状态": report_result.get("status"),
        "报告类型": report_result.get("report_type"),
        "标题": report_result.get("title"),
        "摘要": report_result.get("executive_summary"),
        "总体评价": report_result.get("overall_assessment"),
        "章节数量": len(report_result.get("sections") or []),
        "风险提示数量": len(report_result.get("risk_warnings") or []),
        "数据限制数量": len(report_result.get("data_limitations") or []),
        "结论": report_result.get("conclusion"),
        "免责声明": report_result.get("disclaimer"),
        "Markdown长度": len(markdown_report),
        "助手消息": state.get("assistant_message"),
        "错误消息": state.get("error_message"),
    }
    if full_results:
        payload["完整报告结果"] = report_result

    print_stage_payload("Report 阶段成果", payload, full_results=full_results)


def print_reflection_stage_output(
    state: WorkflowState,
    *,
    full_results: bool,
) -> None:
    reflection_result = state.get("reflection_result") or {}
    final_report_markdown = reflection_result.get("final_report_markdown") or ""
    payload = {
        "状态": state.get("status"),
        "当前阶段": state.get("current_stage"),
        "下一步": state.get("next_step"),
        "审查状态": reflection_result.get("status"),
        "审查决定": reflection_result.get("decision"),
        "建议下一阶段": reflection_result.get("recommended_next_stage"),
        "审查摘要": reflection_result.get("summary"),
        "问题数量": len(reflection_result.get("issues") or []),
        "修订指令数量": len(reflection_result.get("revision_instructions") or []),
        "修订后报告长度": len(final_report_markdown),
        "给 Supervisor 的说明": reflection_result.get("notes_for_supervisor"),
        "助手消息": state.get("assistant_message"),
        "错误消息": state.get("error_message"),
    }
    if full_results:
        payload["完整审查结果"] = reflection_result

    print_stage_payload("Reflection 阶段成果", payload, full_results=full_results)


def summarize_financial_data(financial_data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for part_name, batches in financial_data.items():
        if not isinstance(batches, list):
            summary[part_name] = {"批次数": 1, "记录数": 1}
            continue

        record_count = 0
        for batch in batches:
            if isinstance(batch, list):
                record_count += len(batch)
            elif batch is not None:
                record_count += 1

        summary[part_name] = {
            "批次数": len(batches),
            "记录数": record_count,
        }
    return summary


def summarize_evidence(evidence_json: Any) -> dict[str, Any]:
    if not isinstance(evidence_json, str) or not evidence_json.strip():
        return {"是否可用": False, "轮数": 0}

    try:
        evidence = json.loads(evidence_json)
    except json.JSONDecodeError as exc:
        return {
            "是否可用": True,
            "JSON是否合法": False,
            "错误": str(exc),
        }

    if not isinstance(evidence, list):
        return {
            "是否可用": True,
            "JSON是否合法": True,
            "类型": type(evidence).__name__,
        }

    tool_names = [
        item.get("tool_name")
        for item in evidence
        if isinstance(item, dict) and item.get("tool_name")
    ]
    return {
        "是否可用": True,
        "JSON是否合法": True,
        "轮数": len(evidence),
        "工具": tool_names,
    }


def print_stage_payload(
    title: str,
    payload: dict[str, Any],
    *,
    full_results: bool,
) -> None:
    print_step(title)
    normalized = normalize_for_json(payload)
    text = json.dumps(normalized, ensure_ascii=False, indent=2, default=str)
    if not full_results and len(text) > MAX_STAGE_OUTPUT_PREVIEW_LENGTH:
        text = text[:MAX_STAGE_OUTPUT_PREVIEW_LENGTH] + "...（已截断）"
    print(text)


def covered_nodes_from_history(state: WorkflowState) -> set[str]:
    covered: set[str] = set()
    for record in state.get("execution_history", []):
        node_name = EXECUTION_AGENT_TO_NODE.get(record.get("agent"))
        if node_name:
            covered.add(node_name)
    return covered


def assert_analysis_stage_outputs(state: WorkflowState) -> None:
    print_step("Analysis 阶段断言")

    analysis_history = [
        record
        for record in state.get("execution_history", [])
        if record.get("agent") == "AnalysisAgent"
    ]
    require(analysis_history, "工作流没有执行 analysis_node。")
    require(
        any(record.get("success") for record in analysis_history),
        f"analysis_node 未成功完成: {analysis_history}",
    )

    analysis_result = state.get("analysis_result")
    require(isinstance(analysis_result, dict), "analysis_result 必须是字典。")
    require(bool(analysis_result), "analysis_result 不能为空。")

    required_keys = {
        "status",
        "summary",
        "dimensions",
        "data_limitations",
        "evidence",
        "conclusion",
    }
    missing_keys = required_keys - set(analysis_result)
    require(not missing_keys, f"analysis_result 缺少字段: {sorted(missing_keys)}")

    require(
        analysis_result["status"] in VALID_ANALYSIS_STATUSES,
        f"未预期的分析状态: {analysis_result['status']}",
    )
    require(
        analysis_result["status"] in NON_FAILED_ANALYSIS_STATUSES,
        "analysis_result.status 为 analysis_failed。",
    )
    require(
        isinstance(analysis_result["summary"], str)
        and bool(analysis_result["summary"].strip()),
        "analysis_result.summary 必须是非空字符串。",
    )
    require(
        isinstance(analysis_result["dimensions"], list),
        "analysis_result.dimensions 必须是列表。",
    )
    require(
        isinstance(analysis_result["data_limitations"], list),
        "analysis_result.data_limitations 必须是列表。",
    )
    require(
        isinstance(analysis_result["evidence"], str)
        and bool(analysis_result["evidence"].strip()),
        "analysis_result.evidence 必须是非空 JSON 字符串。",
    )
    require(
        isinstance(analysis_result["conclusion"], str)
        and bool(analysis_result["conclusion"].strip()),
        "analysis_result.conclusion 必须是非空字符串。",
    )

    try:
        evidence = json.loads(analysis_result["evidence"])
    except json.JSONDecodeError as exc:
        raise AssertionError(f"analysis_result.evidence 不是合法 JSON: {exc}") from exc
    require(isinstance(evidence, list), "analysis_result.evidence 的 JSON 内容必须是列表。")

    require(
        state.get("last_completed_stage") in {
            WorkflowStep.ANALYSIS.value,
            WorkflowStep.REPORT.value,
            WorkflowStep.REFLECTION.value,
            WorkflowStep.FINISHED.value,
        },
        (
            "analysis 执行后 last_completed_stage 应为 analysis 或后续阶段；"
            f"实际值为 {state.get('last_completed_stage')!r}。"
        ),
    )

    print("analysis_node 已成功执行。")
    print(f"分析状态: {analysis_result['status']}")
    print(f"分析维度数量: {len(analysis_result['dimensions'])}")
    print(f"证据工具轮数: {len(evidence)}")

    preview = normalize_for_json(analysis_result)
    preview_text = json.dumps(preview, ensure_ascii=False, indent=2, default=str)
    print("analysis_result 完整内容:")
    print(preview_text)


def assert_report_stage_outputs(state: WorkflowState) -> None:
    print_step("Report 阶段断言")

    report_history = [
        record
        for record in state.get("execution_history", [])
        if record.get("agent") == "ReportAgent"
    ]
    require(report_history, "工作流没有执行 report_node。")
    require(
        any(record.get("success") for record in report_history),
        f"report_node 未成功完成: {report_history}",
    )

    report_result = state.get("report_result")
    require(isinstance(report_result, dict), "report_result 必须是字典。")
    require(bool(report_result), "report_result 不能为空。")

    required_keys = {
        "status",
        "report_type",
        "title",
        "executive_summary",
        "overall_assessment",
        "sections",
        "risk_warnings",
        "data_limitations",
        "conclusion",
        "disclaimer",
        "markdown_report",
    }
    missing_keys = required_keys - set(report_result)
    require(not missing_keys, f"report_result 缺少字段: {sorted(missing_keys)}")

    require(
        report_result["status"] in VALID_REPORT_STATUSES,
        f"未预期的报告状态: {report_result['status']}",
    )
    require(
        report_result["status"] in NON_FAILED_REPORT_STATUSES,
        "report_result.status 为 report_failed。",
    )
    analysis_status = (state.get("analysis_result") or {}).get("status")
    expected_report_statuses = {
        "analysis_done": {"report_ready"},
        "analysis_partial": {"report_partial"},
        "needs_more_data": {"report_partial"},
    }
    if analysis_status in expected_report_statuses:
        require(
            report_result["status"] in expected_report_statuses[analysis_status],
            (
                "report_result.status 与 analysis_result.status 不匹配: "
                f"analysis={analysis_status}, report={report_result['status']}"
            ),
        )
    require(
        report_result["report_type"] in VALID_REPORT_TYPES,
        f"未预期的报告类型: {report_result['report_type']}",
    )

    for field_name in (
        "title",
        "executive_summary",
        "conclusion",
        "disclaimer",
        "markdown_report",
    ):
        value = report_result[field_name]
        require(
            isinstance(value, str) and bool(value.strip()),
            f"report_result.{field_name} 必须是非空字符串。",
        )

    overall_assessment = report_result["overall_assessment"]
    require(
        isinstance(overall_assessment, dict),
        "report_result.overall_assessment 必须是字典。",
    )
    assessment_required_keys = {"score", "label", "basis", "confidence"}
    assessment_missing_keys = assessment_required_keys - set(overall_assessment)
    require(
        not assessment_missing_keys,
        f"overall_assessment 缺少字段: {sorted(assessment_missing_keys)}",
    )
    require(
        overall_assessment.get("confidence") in VALID_CONFIDENCE_LEVELS,
        f"overall_assessment.confidence 非法: {overall_assessment.get('confidence')}",
    )

    sections = report_result["sections"]
    require(isinstance(sections, list), "report_result.sections 必须是列表。")
    require(bool(sections), "report_result.sections 不能为空。")
    for index, section in enumerate(sections, start=1):
        require(isinstance(section, dict), f"第 {index} 个 section 必须是字典。")
        for field_name in ("heading", "summary"):
            value = section.get(field_name)
            require(
                isinstance(value, str) and bool(value.strip()),
                f"第 {index} 个 section.{field_name} 必须是非空字符串。",
            )
        require(
            isinstance(section.get("key_points"), list),
            f"第 {index} 个 section.key_points 必须是列表。",
        )
        require(
            isinstance(section.get("supporting_metrics"), list),
            f"第 {index} 个 section.supporting_metrics 必须是列表。",
        )

    require(
        isinstance(report_result["risk_warnings"], list),
        "report_result.risk_warnings 必须是列表。",
    )
    require(
        isinstance(report_result["data_limitations"], list),
        "report_result.data_limitations 必须是列表。",
    )

    markdown_report = report_result["markdown_report"]
    require(
        markdown_report.lstrip().startswith("#"),
        "report_result.markdown_report 应以 Markdown 标题开头。",
    )
    require(
        "```" not in markdown_report,
        "report_result.markdown_report 不应包含 Markdown 代码块。",
    )
    require(
        "数据限制" in markdown_report,
        "report_result.markdown_report 缺少数据限制章节。",
    )
    require(
        "免责声明" in markdown_report,
        "report_result.markdown_report 缺少免责声明章节。",
    )

    require(
        state.get("last_completed_stage") in {
            WorkflowStep.REPORT.value,
            WorkflowStep.REFLECTION.value,
            WorkflowStep.FINISHED.value,
        },
        (
            "report 执行后 last_completed_stage 应为 report 或后续阶段；"
            f"实际值为 {state.get('last_completed_stage')!r}。"
        ),
    )

    print("report_node 已成功执行。")
    print(f"报告状态: {report_result['status']}")
    print(f"报告类型: {report_result['report_type']}")
    print(f"报告章节数量: {len(sections)}")
    print(f"Markdown 报告长度: {len(markdown_report)}")

    preview = normalize_for_json(report_result)
    preview_text = json.dumps(preview, ensure_ascii=False, indent=2, default=str)
    print("report_result 完整内容:")
    print(preview_text)


def assert_reflection_stage_outputs(state: WorkflowState) -> None:
    print_step("Reflection 阶段断言")

    reflection_history = [
        record
        for record in state.get("execution_history", [])
        if record.get("agent") == "ReflectionAgent"
    ]
    require(reflection_history, "工作流没有执行 reflection_node。")
    require(
        any(record.get("success") for record in reflection_history),
        f"reflection_node 未成功完成: {reflection_history}",
    )

    reflection_result = state.get("reflection_result")
    require(isinstance(reflection_result, dict), "reflection_result 必须是字典。")
    require(bool(reflection_result), "reflection_result 不能为空。")

    required_keys = {
        "status",
        "decision",
        "recommended_next_stage",
        "summary",
        "issues",
        "revision_instructions",
        "final_report_markdown",
        "notes_for_supervisor",
    }
    missing_keys = required_keys - set(reflection_result)
    require(not missing_keys, f"reflection_result 缺少字段: {sorted(missing_keys)}")

    status = reflection_result["status"]
    decision = reflection_result["decision"]
    recommended_next_stage = reflection_result["recommended_next_stage"]
    require(
        status in VALID_REFLECTION_STATUSES,
        f"未预期的审查状态: {status}",
    )
    require(
        status in NON_FAILED_REFLECTION_STATUSES,
        "reflection_result.status 为 reflection_failed。",
    )
    require(
        decision in VALID_REFLECTION_DECISIONS,
        f"未预期的审查决定: {decision}",
    )
    require(
        recommended_next_stage == REFLECTION_DECISION_TO_NEXT_STAGE[decision],
        (
            "reflection_result 路由建议与 decision 不匹配: "
            f"decision={decision}, recommended_next_stage={recommended_next_stage}"
        ),
    )
    require(
        decision in DELIVERABLE_REFLECTION_DECISIONS,
        f"最终 Reflection 结果未达到可交付状态: {decision}",
    )
    require(
        isinstance(reflection_result["summary"], str)
        and bool(reflection_result["summary"].strip()),
        "reflection_result.summary 必须是非空字符串。",
    )

    issues = reflection_result["issues"]
    require(isinstance(issues, list), "reflection_result.issues 必须是列表。")
    for index, issue in enumerate(issues, start=1):
        require(isinstance(issue, dict), f"第 {index} 个 issue 必须是字典。")
        issue_missing_keys = {
            "type",
            "severity",
            "location",
            "description",
            "suggestion",
        } - set(issue)
        require(
            not issue_missing_keys,
            f"第 {index} 个 issue 缺少字段: {sorted(issue_missing_keys)}",
        )
        require(
            issue.get("severity") in VALID_REFLECTION_ISSUE_SEVERITIES,
            f"第 {index} 个 issue.severity 非法: {issue.get('severity')}",
        )

    revision_instructions = reflection_result["revision_instructions"]
    require(
        isinstance(revision_instructions, list),
        "reflection_result.revision_instructions 必须是列表。",
    )
    notes_for_supervisor = reflection_result["notes_for_supervisor"]
    require(
        isinstance(notes_for_supervisor, list),
        "reflection_result.notes_for_supervisor 必须是列表。",
    )

    final_report_markdown = reflection_result["final_report_markdown"]
    if decision == "pass":
        require(
            final_report_markdown is None,
            "decision 为 pass 时 final_report_markdown 必须为 null。",
        )
    elif decision == "pass_with_minor_revision":
        require(
            isinstance(final_report_markdown, str)
            and bool(final_report_markdown.strip()),
            "轻量修订通过时 final_report_markdown 必须为非空字符串。",
        )

    require(
        state.get("last_completed_stage") in {
            WorkflowStep.REFLECTION.value,
            WorkflowStep.FINISHED.value,
        },
        (
            "reflection 执行后 last_completed_stage 应为 reflection 或 finished；"
            f"实际值为 {state.get('last_completed_stage')!r}。"
        ),
    )

    print("reflection_node 已成功执行。")
    print(f"审查状态: {status}")
    print(f"审查决定: {decision}")
    print(f"发现问题数量: {len(issues)}")
    print(f"修订指令数量: {len(revision_instructions)}")

    output = normalize_for_json(reflection_result)
    output_text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
    print("reflection_result 完整内容:")
    print(output_text)


def run_graph_scheduling_check(
    nodes: WorkflowNodes,
    data_nodes: DataSubgraphNodes,
    query: str,
    node_result_records: list[dict[str, Any]],
    *,
    full_results: bool,
) -> tuple[WorkflowState, set[str]]:
    print_step("图调度检查：运行到 Reflection 阶段")
    graph = WorkflowGraph(
        nodes=nodes,
        data_nodes=data_nodes,
        max_iterations=40,
        enable_trace=False,
    )

    record_start_index = len(node_result_records)
    final_state = graph.run(query)
    graph_node_records = node_result_records[record_start_index:]

    print(f"最终状态: {enum_value(final_state.get('status'))}")
    print(f"当前阶段: {enum_value(final_state.get('current_stage'))}")
    print(f"下一步: {enum_value(final_state.get('next_step'))}")
    print_execution_history(final_state)

    print_node_run_results(
        graph_node_records,
        title="图运行期间捕获的节点真实返回",
        full_results=full_results,
    )

    assert_graph_node_outputs(final_state)
    assert_analysis_stage_outputs(final_state)
    assert_report_stage_outputs(final_state)
    assert_reflection_stage_outputs(final_state)

    covered = covered_nodes_from_history(final_state)
    missing_nodes = EXPECTED_GRAPH_NODES - covered
    require(not missing_nodes, f"图未调度这些节点: {sorted(missing_nodes)}")

    print("已覆盖的图节点:")
    for node_name in sorted(covered):
        print(f"  - {node_name}")

    return final_state, covered


def main() -> None:
    args = parse_args()

    print_step("集成测试输入")
    print("本脚本使用真实配置服务:")
    print("  - OpenAIClient：用于规划、Supervisor 审查、Analysis、Report 和 Reflection LLM 调用")
    print("  - SessionLocal 和 repositories：用于访问本地财务数据库")
    print("  - TushareService：在需要数据回填时访问 TuShare")
    print(f"用户输入: {args.query}")

    nodes, data_nodes = build_real_nodes()
    assert_real_dependencies(nodes, data_nodes)
    create_missing_tables_from_orm()
    assert_database_schema_matches_models()
    node_result_records = attach_node_result_recorder_with_stage_prints(
        nodes,
        data_nodes,
        full_results=args.full_results,
    )

    final_state, _covered = run_graph_scheduling_check(
        nodes=nodes,
        data_nodes=data_nodes,
        query=args.query,
        node_result_records=node_result_records,
        full_results=args.full_results,
    )

    assert_state_json_safe(final_state)

    print_step("完成")
    print("Supervisor + Data + Analysis + Report + Reflection 真实集成检查完成。")


if __name__ == "__main__":
    main()
