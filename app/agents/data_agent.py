"""DataAgent: plans which data parts the data stage should fetch."""

from __future__ import annotations

from app.workflows.state import (
    CORE_DATA_PARTS,
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_COMPANY_PROFILE,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    WorkflowState,
    WorkflowStatus,
)


class DataAgent:
    """Data-stage planner.

    The agent decides which deterministic data nodes should run. LangGraph is
    responsible for scheduling those nodes in parallel.
    """

    def run(self, state: WorkflowState) -> dict:
        required_parts = self.plan_required_parts(state)
        return {
            "required_data_parts": required_parts,
            "status": WorkflowStatus.DATA_PLANNED,
            "assistant_message": (
                "DataAgent planned data requirements: " + ", ".join(required_parts)
            ),
        }

    def plan_required_parts(self, state: WorkflowState) -> list[str]:
        focus = (state.get("analysis_focus") or "").lower()
        query = (state.get("user_query") or "").lower()
        text = f"{focus} {query}"

        parts = {DATA_PART_COMPANY_PROFILE}

        if any(keyword in text for keyword in ["profit", "revenue", "income", "盈利", "利润", "收入"]):
            parts.update({DATA_PART_INCOME, DATA_PART_INDICATORS})

        if any(keyword in text for keyword in ["debt", "solvency", "liability", "偿债", "负债", "资产"]):
            parts.update({DATA_PART_BALANCE, DATA_PART_INDICATORS})

        if any(keyword in text for keyword in ["cash", "现金流", "现金"]):
            parts.update({DATA_PART_CASHFLOW})

        if any(keyword in text for keyword in ["growth", "综合", "财务", "report", "报告", "分析"]):
            parts.update(CORE_DATA_PARTS)

        # If the planner gave no strong signal, use the full conservative set.
        if len(parts) == 1:
            parts.update(CORE_DATA_PARTS)

        return [part for part in CORE_DATA_PARTS if part in parts]
