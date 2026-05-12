"""DataAgent: plans which data parts the data stage should fetch."""

from __future__ import annotations

from typing import Any

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
    def __init__(self, required_parts_skill, backfill_plan_skill):
        self.required_parts_skill = required_parts_skill
        self.backfill_plan_skill = backfill_plan_skill

    def run(self, state: WorkflowState) -> dict:
        if not state.get("financial_data"):
            return self._plan_required_parts(state)
        else:
            return self._decide_backfill(state)


    def _plan_required_parts(self, state: WorkflowState) -> dict[str, Any]:
        results = self.required_parts_skill.plan_required_parts(
            state.get("user_query"),
            state.get("analysis_focus")
        )
        return {
            "required_data_parts": results.get("required_data_parts"),
            "assistant_message": results.get("note")
        }

    def _decide_backfill(self, state: WorkflowState) -> dict[str, Any]:
        llm_judge_results = self.backfill_plan_skill.backfill_plan(
            analysis_focus=state.get("analysis_focus"),
            data_completeness_check_result=state.get("data_completeness_check_result"),
        ) or {}
        return llm_judge_results