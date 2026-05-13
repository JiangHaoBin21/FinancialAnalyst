# app/workflows/subgraphs/data_graph.py

from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph

from app.workflows.state import WorkflowState
from app.workflows.subgraphs.data_nodes import DataSubgraphNodes
from app.workflows.subgraphs.data_routes import (
    data_route_path_map,
    route_data_parts,
)


def build_data_subgraph(
    *,
    nodes: DataSubgraphNodes,
    wrap_node: Callable | None = None,
):
    """构建 DataSubgraph。"""
    builder = StateGraph(WorkflowState)

    def node(fn):
        return wrap_node(fn) if wrap_node else fn

    builder.add_node("data_planner", node(nodes.data_planner_node))
    builder.add_node("prepare_company_context", node(nodes.prepare_company_context_node))
    builder.add_node("fetch_income_statement", node(nodes.fetch_income_statement_node))
    builder.add_node("fetch_balance_sheet", node(nodes.fetch_balance_sheet_node))
    builder.add_node("fetch_cashflow_statement", node(nodes.fetch_cashflow_statement_node))
    builder.add_node("fetch_financial_indicator", node(nodes.fetch_financial_indicator_node))
    builder.add_node("data_merge", node(nodes.data_merge_node))
    builder.add_node("completeness_check", node(nodes.completeness_check_node))
    builder.add_node("backfill_planner", node(nodes.backfill_planner_node))
    builder.add_node("data_finalize", node(nodes.data_finalize_node))
    builder.add_node("data_error", node(nodes.data_error_node))

    builder.add_edge(START, "data_planner")
    builder.add_edge("data_planner", "prepare_company_context")

    builder.add_conditional_edges(
        "prepare_company_context",
        route_data_parts,
        data_route_path_map(),
    )

    for fetch_node in (
        "fetch_income_statement",
        "fetch_balance_sheet",
        "fetch_cashflow_statement",
        "fetch_financial_indicator",
    ):
        builder.add_edge(fetch_node, "data_merge")

    builder.add_edge("data_merge", "completeness_check")
    builder.add_edge("completeness_check", "backfill_planner")

    builder.add_conditional_edges(
        "backfill_planner",
        route_data_parts,
        data_route_path_map(),
    )

    builder.add_edge("data_finalize", END)
    builder.add_edge("data_error", END)

    return builder.compile()