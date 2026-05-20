from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, is_dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from threading import Lock
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.analysis_agent import AnalysisAgent
from app.agents.data_agent import DataAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.report_agent import ReportAgent
from app.agents.supervisor_agent import SupervisorAgent
from app.core.config import settings
from app.core.database import SessionLocal
from app.llms.openai_client import OpenAIClient
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
from app.workflows.graph import WorkflowGraph
from app.workflows.nodes import WorkflowNodes
from app.workflows.subgraphs.data_nodes import DataSubgraphNodes
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    WorkflowState,
    WorkflowStatus,
    create_initial_state,
    normalize_for_json,
)


DEFAULT_QUERY = (
    "请分析 300750.SZ 在 2023 年的综合财务表现，覆盖盈利能力、偿债能力、"
    "现金流质量和核心财务指标，并生成报告。"
)

MAX_PREVIEW_ITEMS = 3
MAX_FULL_LIST_ITEMS = 10
MAX_TEXT_LENGTH = 500
MAX_JSON_SAFETY_ISSUES = 80

FINANCIAL_PARTS = [
    DATA_PART_INCOME,
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INDICATORS,
]

EXPECTED_NODES = {
    "supervisor_node",
    "await_user_input_node",
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
}

EXPECTED_GRAPH_NODES = EXPECTED_NODES - {"await_user_input_node"}

MAIN_NODE_METHOD_NAMES = [
    "supervisor_node",
    "await_user_input_node",
    "analysis_node",
    "report_node",
    "reflection_node",
    "finish_node",
    "error_node",
]

DATA_NODE_METHOD_NAMES = [
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
]

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
}


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
            "运行 supervisor 和 data 阶段节点的真实集成检查。"
            "脚本会调用当前配置的 LLM、数据库和 TuShare 服务。"
        )
    )
    parser.add_argument(
        "-h",
        "--帮助",
        action="help",
        help="显示帮助信息并退出。",
    )
    parser.add_argument(
        "--用户输入",
        dest="query",
        default=DEFAULT_QUERY,
        metavar="文本",
        help="发送给真实 SupervisorAgent 和规划 LLM 的用户输入。",
    )
    parser.add_argument(
        "--query",
        dest="query",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--完整结果",
        dest="full_results",
        action="store_true",
        help="打印每个节点返回的完整结果；默认会压缩长列表和长文本。",
    )
    return parser.parse_args()


def build_real_nodes() -> tuple[WorkflowNodes, DataSubgraphNodes]:
    settings.validate()

    llm_client = OpenAIClient()
    planning_skill = PlanningSkill(llm_client=llm_client)
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
        supervisor_agent=SupervisorAgent(planning_skill=planning_skill),
        analysis_agent=AnalysisAgent(),
        report_agent=ReportAgent(),
        reflection_agent=ReflectionAgent(),
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def print_step(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def attach_node_result_recorder(
    nodes: WorkflowNodes,
    data_nodes: DataSubgraphNodes,
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
            return update

        return wrapped

    for target, node_names in (
        (nodes, MAIN_NODE_METHOD_NAMES),
        (data_nodes, DATA_NODE_METHOD_NAMES),
    ):
        for node_name in node_names:
            original_node = getattr(target, node_name)
            setattr(target, node_name, wrap_node(node_name, original_node))

    return records


def compact_for_print(value: Any, *, full_results: bool, depth: int = 0) -> Any:
    normalized = normalize_for_json(value)
    if full_results:
        return normalized

    if isinstance(normalized, dict):
        if depth >= 4:
            return {
                "类型": "dict",
                "字段数": len(normalized),
                "字段预览": list(normalized.keys())[:MAX_PREVIEW_ITEMS],
            }
        return {
            key: compact_for_print(item, full_results=full_results, depth=depth + 1)
            for key, item in normalized.items()
        }

    if isinstance(normalized, list):
        if _can_print_complete_list(normalized, depth):
            return [
                compact_for_print(item, full_results=full_results, depth=depth + 1)
                for item in normalized
            ]

        preview_count = min(len(normalized), MAX_PREVIEW_ITEMS)
        preview = [
            compact_for_print(item, full_results=full_results, depth=depth + 1)
            for item in normalized[:preview_count]
        ]
        return {
            "类型": "list",
            "实际数量": len(normalized),
            "打印方式": f"仅显示前 {preview_count} 项预览",
            "省略数量": max(len(normalized) - preview_count, 0),
            "预览": preview,
        }

    if isinstance(normalized, str) and len(normalized) > MAX_TEXT_LENGTH:
        return normalized[:MAX_TEXT_LENGTH] + "...（已截断）"

    return normalized


def _can_print_complete_list(items: list[Any], depth: int) -> bool:
    if len(items) <= MAX_PREVIEW_ITEMS:
        return True
    if depth >= 4 or len(items) > MAX_FULL_LIST_ITEMS:
        return False

    for item in items:
        if isinstance(item, list):
            return False
        if isinstance(item, dict) and _contains_large_nested_collection(item):
            return False
    return True


def _contains_large_nested_collection(value: Any) -> bool:
    if isinstance(value, list):
        return len(value) > MAX_PREVIEW_ITEMS or any(
            _contains_large_nested_collection(item)
            for item in value
        )
    if isinstance(value, dict):
        return any(_contains_large_nested_collection(item) for item in value.values())
    return False


def print_node_run_results(
    records: list[dict[str, Any]],
    *,
    title: str,
    full_results: bool,
) -> None:
    print_step(title)
    if not records:
        print("没有捕获到节点返回结果。")
        return

    for index, record in enumerate(records, 1):
        result = "成功" if record["success"] else "失败"
        print(f"\n{index}. 节点: {record['node_name']} | 运行结果: {result}")

        if "exception_type" in record:
            print(f"  异常类型: {record['exception_type']}")
            print(f"  异常信息: {record['exception_message']}")
            continue

        compacted_update = compact_for_print(
            record.get("update", {}),
            full_results=full_results,
        )
        print("  真实返回 update:")
        print(json.dumps(compacted_update, ensure_ascii=False, indent=2, default=str))


def print_node_update(node_name: str, update: dict[str, Any]) -> None:
    print(f"{node_name}: 成功")
    if "status" in update:
        print(f"  状态: {enum_value(update['status'])}")
    if "next_step" in update:
        print(f"  下一步: {enum_value(update['next_step'])}")
    if "assistant_message" in update and update["assistant_message"]:
        print(f"  消息: {update['assistant_message']}")
    if update.get("has_error"):
        print(f"  错误: {update.get('error_message')}")


def covered_nodes_from_history(state: WorkflowState) -> set[str]:
    covered: set[str] = set()
    for record in state.get("execution_history", []):
        node_name = EXECUTION_AGENT_TO_NODE.get(record.get("agent"))
        if node_name:
            covered.add(node_name)
    return covered


def print_execution_history(state: WorkflowState) -> None:
    print("  图执行记录:")
    for index, record in enumerate(state.get("execution_history", []), 1):
        result = "成功" if record.get("success") else "失败"
        print(
            f"    {index}. {record.get('agent')} | 阶段={record.get('step')} | "
            f"结果={result} | 消息={record.get('message')}"
        )


def scan_non_json_safe_values(
    value: Any,
    *,
    path: str = "$",
    max_issues: int = MAX_JSON_SAFETY_ISSUES,
) -> tuple[list[dict[str, str]], int]:
    """扫描 raw state 中不属于 JSON-native 类型的对象。"""
    issues: list[dict[str, str]] = []
    total_issue_count = 0
    active_object_ids: set[int] = set()

    def add_issue(issue_path: str, issue_value: Any, reason: str) -> None:
        nonlocal total_issue_count
        total_issue_count += 1
        if len(issues) >= max_issues:
            return

        issues.append(
            {
                "path": issue_path,
                "type": _qualified_type_name(issue_value),
                "reason": reason,
                "preview": _preview_value(issue_value),
            }
        )

    def scan(current_value: Any, current_path: str) -> None:
        if isinstance(current_value, Enum):
            add_issue(
                current_path,
                current_value,
                "Enum 实例不是 JSON-native 值，请写入 .value。",
            )
            return

        if current_value is None or isinstance(current_value, (str, bool, int)):
            return

        if isinstance(current_value, float):
            if not isfinite(current_value):
                add_issue(current_path, current_value, "非有限 float 不是标准 JSON 数值。")
            return

        if is_dataclass(current_value) and not isinstance(current_value, type):
            add_issue(
                current_path,
                current_value,
                "dataclass 实例不是 JSON-native 对象，请先转换为 dict。",
            )
            if not _enter_container(current_value, current_path):
                return
            try:
                for field in fields(current_value):
                    scan(
                        getattr(current_value, field.name),
                        _join_json_path(current_path, field.name),
                    )
            finally:
                active_object_ids.remove(id(current_value))
            return

        if isinstance(current_value, dict):
            if type(current_value) is not dict:
                add_issue(
                    current_path,
                    current_value,
                    "dict 子类不是严格 JSON-native 对象，请转换为普通 dict。",
                )
            if not _enter_container(current_value, current_path):
                return
            try:
                for key, item in current_value.items():
                    if not isinstance(key, str):
                        add_issue(
                            f"{current_path}<key:{_preview_value(key)}>",
                            key,
                            "JSON object key 应为 str。",
                        )
                    scan(item, _join_json_path(current_path, key))
            finally:
                active_object_ids.remove(id(current_value))
            return

        if isinstance(current_value, list):
            if type(current_value) is not list:
                add_issue(
                    current_path,
                    current_value,
                    "list 子类不是严格 JSON-native 数组，请转换为普通 list。",
                )
            if not _enter_container(current_value, current_path):
                return
            try:
                for index, item in enumerate(current_value):
                    scan(item, f"{current_path}[{index}]")
            finally:
                active_object_ids.remove(id(current_value))
            return

        if isinstance(current_value, tuple):
            add_issue(
                current_path,
                current_value,
                "tuple 不是 JSON-native 数组，请转换为 list。",
            )
            if not _enter_container(current_value, current_path):
                return
            try:
                for index, item in enumerate(current_value):
                    scan(item, f"{current_path}[{index}]")
            finally:
                active_object_ids.remove(id(current_value))
            return

        add_issue(current_path, current_value, "该对象类型不能直接安全写入 JSON。")

    def _enter_container(container_value: Any, container_path: str) -> bool:
        object_id = id(container_value)
        if object_id in active_object_ids:
            add_issue(container_path, container_value, "存在循环引用，无法 JSON 序列化。")
            return False
        active_object_ids.add(object_id)
        return True

    scan(value, path)
    return issues, total_issue_count


def assert_state_json_safe(state: WorkflowState) -> None:
    print_step("State JSON-safe 检查")
    issues, total_issue_count = scan_non_json_safe_values(state)

    if not issues:
        json.dumps(state, ensure_ascii=False, allow_nan=False)
        print("final_state 未发现非 JSON-safe 对象。")
        return

    print(
        f"final_state 发现 {total_issue_count} 个非 JSON-safe 对象，"
        f"以下展示前 {len(issues)} 个:"
    )
    for index, issue in enumerate(issues, 1):
        print(
            f"  {index}. path={issue['path']} | type={issue['type']} | "
            f"reason={issue['reason']} | preview={issue['preview']}"
        )

    _print_normalized_json_probe(state)
    raise AssertionError(f"final_state 包含 {total_issue_count} 个非 JSON-safe 对象")


def _print_normalized_json_probe(state: WorkflowState) -> None:
    try:
        json.dumps(normalize_for_json(state), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        print(f"normalize_for_json(final_state) 仍无法 JSON 序列化: {exc}")
        return

    print("normalize_for_json(final_state) 可以 JSON 序列化，但 raw final_state 不是 JSON-safe。")


def _join_json_path(base_path: str, key: Any) -> str:
    if isinstance(key, str) and key.isidentifier():
        return f"{base_path}.{key}"
    return f"{base_path}[{json.dumps(str(key), ensure_ascii=False)}]"


def _qualified_type_name(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _preview_value(value: Any) -> str:
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr failed: {type(exc).__name__}: {exc}>"
    text = " ".join(text.splitlines())
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH] + "...（已截断）"
    return text


def assert_graph_node_outputs(state: WorkflowState) -> None:
    require(not state.get("has_error"), f"图执行失败: {state.get('error_message')}")
    required_parts = set(state.get("required_data_parts", []))
    require(
        set(FINANCIAL_PARTS).issubset(required_parts),
        (
            "图执行后 DataAgent 未选择全部财务数据分片。"
            f"实际数据分片={state.get('required_data_parts')}"
        ),
    )
    require(bool(state.get("company_profile")), "图执行后公司画像为空")

    fetched_parts = {
        result.get("part_name")
        for result in state.get("data_part_results", [])
        if result.get("success")
    }
    require(
        set(FINANCIAL_PARTS).issubset(fetched_parts),
        f"图执行后数据抓取分片不完整: {sorted(fetched_parts)}",
    )
    require(bool(state.get("financial_data")), "图执行后合并财务数据为空")
    require(
        "has_missing_data" in state.get("data_completeness_check_result", {}),
        "图执行后缺少数据完整性检查结果",
    )
    require(state.get("current_step_index", 0) >= 1, "图执行后 DataAgent 计划步骤未完成")


def run_graph_scheduling_check(
    nodes: WorkflowNodes,
    data_nodes: DataSubgraphNodes,
    query: str,
    node_result_records: list[dict[str, Any]],
    *,
    full_results: bool,
) -> tuple[WorkflowState, set[str]]:
    print_step("图调度检查 - 使用真实 WorkflowGraph 调度到各节点")
    graph = WorkflowGraph(
        nodes=nodes,
        data_nodes=data_nodes,
        max_iterations=30,
        enable_trace=False,
    )
    record_start_index = len(node_result_records)
    final_state = graph.run(query)
    graph_node_records = node_result_records[record_start_index:]

    print(f"  最终状态: {enum_value(final_state.get('status'))}")
    print(f"  当前阶段: {enum_value(final_state.get('current_stage'))}")
    print(f"  下一步: {enum_value(final_state.get('next_step'))}")
    print_execution_history(final_state)

    assert_graph_node_outputs(final_state)

    covered = covered_nodes_from_history(final_state)
    missing_nodes = EXPECTED_GRAPH_NODES - covered
    require(not missing_nodes, f"图未调度到这些节点: {sorted(missing_nodes)}")

    print("  图已调度到的调度/数据阶段节点:")
    for node_name in sorted(covered):
        print(f"    - {node_name}")

    print_node_run_results(
        graph_node_records,
        title="图调度过程中每个节点的真实返回结果",
        full_results=full_results,
    )
    return final_state, covered


def run_await_user_input_probe(
    nodes: WorkflowNodes,
    covered: set[str],
    node_result_records: list[dict[str, Any]],
    *,
    full_results: bool,
) -> None:
    print_step("节点功能补充检查 - await_user_input_node")
    record_start_index = len(node_result_records)
    update = nodes.await_user_input_node(
        {
            **create_initial_state(user_query=""),
            "assistant_message": "集成检查暂停节点探测。",
            "missing_fields": ["probe_only"],
        }
    )
    covered.add("await_user_input_node")
    print_node_update("await_user_input_node", update)
    require(
        update["status"] == WorkflowStatus.NEEDS_USER_INPUT.value,
        "await_user_input_node 未设置 NEEDS_USER_INPUT 状态",
    )
    print_node_run_results(
        node_result_records[record_start_index:],
        title="补充检查节点的真实返回结果",
        full_results=full_results,
    )


def main() -> None:
    args = parse_args()
    covered: set[str] = set()

    print_step("集成检查输入")
    print("本脚本使用真实配置的服务:")
    print("  - 通过 OpenAIClient/PlanningSkill/SupervisorAgent 调用 LLM")
    print("  - 通过 SessionLocal 和 repositories 访问数据库")
    print("  - 公司查询或回源需要时通过 TushareService 访问 TuShare")
    print(f"用户输入: {args.query}")

    nodes, data_nodes = build_real_nodes()
    node_result_records = attach_node_result_recorder(nodes, data_nodes)

    state, graph_covered = run_graph_scheduling_check(
        nodes,
        data_nodes,
        args.query,
        node_result_records,
        full_results=args.full_results,
    )
    covered.update(graph_covered)
    run_await_user_input_probe(
        nodes,
        covered,
        node_result_records,
        full_results=args.full_results,
    )

    missing_nodes = EXPECTED_NODES - covered
    require(not missing_nodes, f"节点覆盖缺失: {sorted(missing_nodes)}")
    require(
        "prepare_company_context_node" in covered,
        "图未调度公司画像节点",
    )
    assert_state_json_safe(state)

    print_step("完成")
    print("已覆盖的调度/数据阶段节点:")
    for node_name in sorted(covered):
        print(f"  - {node_name}")
    print("\n真实 supervisor/data 节点集成检查完成。")


if __name__ == "__main__":
    main()
