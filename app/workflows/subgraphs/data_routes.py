# app/workflows/subgraphs/data_routes.py

from __future__ import annotations

from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    WorkflowState,
    WorkflowStatus,
)


VALID_DATA_PARTS = {
    DATA_PART_INCOME,
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_INDICATORS,
}


def data_route_path_map() -> dict[str, str]:
    return {
        DATA_PART_INCOME: "fetch_income_statement",
        DATA_PART_BALANCE: "fetch_balance_sheet",
        DATA_PART_CASHFLOW: "fetch_cashflow_statement",
        DATA_PART_INDICATORS: "fetch_financial_indicator",
        "data_finalize": "data_finalize",
        "data_error": "data_error"
    }


def route_data_parts(state: WorkflowState) -> list[str]:
    if state.get("has_error") or state.get("status") == WorkflowStatus.ERROR:
        return ["data_error"]

    if state.get("data_summary"):
        return ["data_finalize"]

    if state.get("need_backfill"):
        already_backfill = int(state.get("already_backfill") or 0)
        if already_backfill > 2:
            return ["data_finalize"]

        routes = [
            part
            for part in state.get("need_backfill", {}).keys()
            if part in VALID_DATA_PARTS
        ]
        return routes or ["data_finalize"]

    routes = [
        part
        for part in state.get("required_data_parts", [])
        if part in VALID_DATA_PARTS
    ]

    return routes or ["data_finalize"]